from __future__ import annotations

from reelagent.intelligence.models import ClaimKind, Evidence, TopicBrief
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
    """Verify material factual claims against independent authoritative evidence."""

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

        claim_indices = _claims_to_verify(brief, quality)
        results: list[ClaimVerificationResult] = []
        for claim_index in claim_indices:
            claim = brief.claims[claim_index]
            request = ClaimVerificationRequest(
                claim_index=claim_index,
                claim_text=claim.text,
                introducing_evidence_ids=claim.evidence_ids,
            )
            introducing_urls = frozenset(
                str(item.source.url)
                for item in brief.evidence
                if item.evidence_id in request.introducing_evidence_ids
            )
            results.append(
                await self.verify_claim(
                    request,
                    excluded_urls=introducing_urls,
                )
            )

        return VerificationReport(outcome=_report_outcome(results), results=tuple(results))

    async def verify_claim(
        self,
        request: ClaimVerificationRequest,
        *,
        excluded_urls: frozenset[str] = frozenset(),
    ) -> ClaimVerificationResult:
        """Verify one claim using the same evidence-safety rules as the full pipeline."""

        collected = await self._evidence_collector.collect(request)
        independent = _independent_authoritative_evidence(
            collected=collected,
            excluded_urls=excluded_urls,
        )
        if not independent:
            return ClaimVerificationResult(
                request=request,
                verdict=ClaimVerificationVerdict.INSUFFICIENT_EVIDENCE,
                rationale="No independent authoritative evidence was collected.",
            )

        result = await self._verifier.verify(request, independent)
        if result.request != request:
            raise ValueError("claim verifier returned a result for a different request")
        if result.verification_evidence != independent:
            raise ValueError("claim verifier changed the authoritative evidence set")
        return result


def _claims_to_verify(brief: TopicBrief, quality: TopicQualityResult) -> tuple[int, ...]:
    requested = set(quality.claims_requiring_independent_verification)
    requested.update(
        index
        for index, claim in enumerate(brief.claims)
        if claim.material and claim.kind == ClaimKind.FACT and claim.verification_required
    )
    invalid = [index for index in requested if index < 0 or index >= len(brief.claims)]
    if invalid:
        raise ValueError(f"quality gate references unknown claim indices: {sorted(invalid)}")
    return tuple(sorted(requested))


def _independent_authoritative_evidence(
    *,
    collected: tuple[Evidence, ...],
    excluded_urls: frozenset[str],
) -> tuple[Evidence, ...]:
    return tuple(
        item
        for item in collected
        if item.source.source_kind not in _NON_AUTHORITATIVE_SOURCE_KINDS
        and str(item.source.url) not in excluded_urls
        and not item.instruction_like_content_detected
    )


def _report_outcome(results: list[ClaimVerificationResult]) -> VerificationOutcome:
    verdicts = {result.verdict for result in results}
    if ClaimVerificationVerdict.UNSUPPORTED in verdicts:
        return VerificationOutcome.REVISION_REQUIRED
    if ClaimVerificationVerdict.INSUFFICIENT_EVIDENCE in verdicts:
        return VerificationOutcome.NEEDS_RESEARCH
    return VerificationOutcome.READY_FOR_SCRIPT
