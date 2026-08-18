from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from reelagent.intelligence.models import ClaimKind, TopicBrief
from reelagent.topics.models import SourceKind


class TopicQualityDecision(StrEnum):
    READY_FOR_VERIFICATION = "ready_for_verification"
    REJECTED = "rejected"


class TopicQualityResult(BaseModel, frozen=True):
    decision: TopicQualityDecision
    reasons: tuple[str, ...] = ()
    claims_requiring_independent_verification: tuple[int, ...] = ()


class TopicQualityGate:
    """Deterministically decide whether a Topic Brief is worth verifying further."""

    def __init__(self, *, min_reel_worthiness_score: int = 65) -> None:
        self._min_score = min_reel_worthiness_score

    def evaluate(self, brief: TopicBrief) -> TopicQualityResult:
        reasons: list[str] = []
        if brief.reel_worthiness.overall_score < self._min_score:
            reasons.append("reel worthiness score is below the configured threshold")
        if not brief.key_insights:
            reasons.append("topic brief has no key technical insights")

        referenced_instruction_like = {
            item.evidence_id
            for item in brief.evidence
            if item.instruction_like_content_detected
        }
        independent_verification: list[int] = []
        for index, claim in enumerate(brief.claims):
            if not claim.material:
                continue
            if claim.kind != ClaimKind.RECOMMENDATION and not claim.evidence_ids:
                reasons.append(f"material claim {index} has no supporting evidence")
            if claim.kind == ClaimKind.FACT and not claim.verification_required:
                reasons.append(f"material factual claim {index} bypasses verification")
            if referenced_instruction_like.intersection(claim.evidence_ids):
                reasons.append(f"material claim {index} relies on instruction-like evidence")

            evidence_by_id = {item.evidence_id: item for item in brief.evidence}
            claim_sources = [
                evidence_by_id[evidence_id].source.source_kind
                for evidence_id in claim.evidence_ids
                if evidence_id in evidence_by_id
            ]
            if claim.kind == ClaimKind.FACT and claim_sources and all(
                source in {SourceKind.HACKER_NEWS, SourceKind.COMMUNITY}
                for source in claim_sources
            ):
                independent_verification.append(index)

        decision = (
            TopicQualityDecision.REJECTED
            if reasons
            else TopicQualityDecision.READY_FOR_VERIFICATION
        )
        return TopicQualityResult(
            decision=decision,
            reasons=tuple(reasons),
            claims_requiring_independent_verification=tuple(independent_verification),
        )
