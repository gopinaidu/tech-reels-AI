from __future__ import annotations

from reelagent.intelligence.models import Evidence, TopicBrief
from reelagent.intelligence.quality import TopicQualityDecision, TopicQualityResult
from reelagent.topics.models import SourceKind
from reelagent.verification.models import (
    ClaimVerificationRequest,
    ClaimVerificationResult,
    ClaimVerificationVerdict,
    VerificationOutcome,
    VerificationReport,
)
from reelagent.verification.ports import ClaimVerifier, VerificationEvidenceCollector

_NON_AUTHORITATIVE_SOURCE_KINDS = {SourceKind.HACKER_NEWS, SourceKind.COMMUNITY}


class VerificationPipeline:
    """Verify factual claims selected by the Topic Intelligence quality gate."""

    def __init__(
        self,
        *,
        evidence_collector: VerificationEvidenceCollector,
        verifier: ClaimVerifier,
    ) -> None:
        self._evidence_collector = evidence_collector
        self._verifier = verifier

    async def run(self, brief: TopicBrief, quality: TopicQualityResult) -> VerificationReport:
        if quality.decision != TopicQualityDecision.READY_FOR_VERIFICATION:
            raise ValueError("verification requires a Topic Brief that passed the quality gate")

        results: list[ClaimVerificationResult] = []
        for claim_index in quality.claims_requiring_independent_verification:
            if claim_index >= len(brief.claims):
                raise ValueError(f"quality gate references unknown claim index: {claim_index}")

            claim = brief.claims[claim_index]
            request = ClaimVerificationRequest(
                claim_index=claim_index,
                claim_text=claim.text,
                introducing_evidence_ids=claim.evidence_ids,
            )
            collected = await self._evidence_collector.collect(request)
            independent = _independent_authoritative_evidence(
                brief=brief,
                request=request,
                collected=collected,
            )
            if not independent:
                results.append(
                    ClaimVerificationResult(
                        request=request,
                        verdict=ClaimVerificationVerdict.INSUFFICIENT_EVIDENCE,
                        rationale="No independent authoritative evidence was collected.",
                    )
                )
                continue

            result = await self._verifier.verify(request, independent)
            if result.request != request:
                raise ValueError("claim verifier returned a result for a different request")
            if result.verification_evidence != independent:
                raise ValueError("claim verifier changed the authoritative evidence set")
            results.append(result)

        return VerificationReport(outcome=_report_outcome(results), results=tuple(results))


def _independent_authoritative_evidence(
    *,
    brief: TopicBrief,
    request: ClaimVerificationRequest,
    collected: tuple[Evidence, ...],
) -> tuple[Evidence, ...]:
    introducing_urls = {
        str(item.source.url)
        for item in brief.evidence
        if item.evidence_id in request.introducing_evidence_ids
    }
    return tuple(
        item
        for item in collected
        if item.source.source_kind not in _NON_AUTHORITATIVE_SOURCE_KINDS
        and str(item.source.url) not in introducing_urls
        and not item.instruction_like_content_detected
    )


def _report_outcome(results: list[ClaimVerificationResult]) -> VerificationOutcome:
    verdicts = {result.verdict for result in results}
    if ClaimVerificationVerdict.UNSUPPORTED in verdicts:
        return VerificationOutcome.REVISION_REQUIRED
    if ClaimVerificationVerdict.INSUFFICIENT_EVIDENCE in verdicts:
        return VerificationOutcome.NEEDS_RESEARCH
    return VerificationOutcome.READY_FOR_SCRIPT
