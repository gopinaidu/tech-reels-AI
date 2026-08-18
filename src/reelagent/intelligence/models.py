from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from reelagent.topics.models import SourceEvidence, TopicCandidate


class EvidenceRole(StrEnum):
    DISCOVERY = "discovery"
    VERIFICATION = "verification"
    INSPIRATION = "inspiration"
    DISCUSSION = "discussion"


class ClaimKind(StrEnum):
    FACT = "fact"
    INTERPRETATION = "interpretation"
    RECOMMENDATION = "recommendation"
    EXPERIENCE = "experience"
    SPECULATION = "speculation"


class DiscussionInsightKind(StrEnum):
    CONSENSUS = "consensus"
    COUNTERARGUMENT = "counterargument"
    PRACTICAL_EXPERIENCE = "practical_experience"
    OPEN_QUESTION = "open_question"


class Evidence(BaseModel, frozen=True):
    """Retrieved source material retained with provenance and intended role."""

    evidence_id: str = Field(min_length=1, max_length=120)
    source: SourceEvidence
    roles: frozenset[EvidenceRole] = Field(min_length=1)
    summary: str = Field(min_length=1, max_length=2_000)
    retrieved_at: datetime
    attribution_required: bool = False
    instruction_like_content_detected: bool = False

    @model_validator(mode="after")
    def retrieved_at_must_be_timezone_aware(self) -> Evidence:
        if self.retrieved_at.tzinfo is None:
            raise ValueError("retrieved_at must be timezone-aware")
        return self


class Claim(BaseModel, frozen=True):
    """A statement in the brief with explicit classification and evidence mapping."""

    text: str = Field(min_length=1, max_length=1_000)
    kind: ClaimKind
    evidence_ids: tuple[str, ...] = ()
    material: bool = True
    verification_required: bool = True

    @model_validator(mode="after")
    def factual_claims_require_evidence(self) -> Claim:
        if self.kind == ClaimKind.FACT and not self.evidence_ids:
            raise ValueError("factual claims must reference at least one evidence item")
        return self


class KeyInsight(BaseModel, frozen=True):
    title: str = Field(min_length=1, max_length=200)
    explanation: str = Field(min_length=1, max_length=1_500)
    claim_indices: tuple[int, ...] = ()


class DiscussionInsight(BaseModel, frozen=True):
    kind: DiscussionInsightKind
    summary: str = Field(min_length=1, max_length=1_500)
    evidence_ids: tuple[str, ...] = Field(min_length=1)


class ReelWorthiness(BaseModel, frozen=True):
    novelty: int = Field(ge=0, le=5)
    technical_depth: int = Field(ge=0, le=5)
    audience_value: int = Field(ge=0, le=5)
    visual_explainability: int = Field(ge=0, le=5)
    overall_score: int = Field(ge=0, le=100)
    rationale: str = Field(min_length=1, max_length=1_000)


class TopicEvidencePackage(BaseModel, frozen=True):
    """Bounded evidence supplied to Topic Intelligence; retrieved text remains untrusted data."""

    topic: TopicCandidate
    evidence: tuple[Evidence, ...] = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def evidence_ids_must_be_unique(self) -> TopicEvidencePackage:
        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence_id values must be unique within a topic evidence package")
        return self


class TopicBrief(BaseModel, frozen=True):
    """Structured Topic Intelligence output consumed by later workflow stages."""

    topic: TopicCandidate
    what_happened: str = Field(min_length=1, max_length=2_000)
    why_it_matters: str = Field(min_length=1, max_length=2_000)
    recommended_angle: str = Field(min_length=1, max_length=500)
    claims: tuple[Claim, ...] = Field(min_length=1, max_length=30)
    key_insights: tuple[KeyInsight, ...] = Field(min_length=1, max_length=10)
    discussion_insights: tuple[DiscussionInsight, ...] = Field(default=(), max_length=10)
    evidence: tuple[Evidence, ...] = Field(min_length=1, max_length=40)
    reel_worthiness: ReelWorthiness
    created_at: datetime

    @model_validator(mode="after")
    def validate_cross_references(self) -> TopicBrief:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")

        evidence_ids = {item.evidence_id for item in self.evidence}
        for claim in self.claims:
            missing = set(claim.evidence_ids) - evidence_ids
            if missing:
                raise ValueError(f"claim references unknown evidence ids: {sorted(missing)}")
        for insight in self.discussion_insights:
            missing = set(insight.evidence_ids) - evidence_ids
            if missing:
                raise ValueError(
                    f"discussion insight references unknown evidence ids: {sorted(missing)}"
                )
        for insight in self.key_insights:
            invalid = [index for index in insight.claim_indices if index < 0 or index >= len(self.claims)]
            if invalid:
                raise ValueError(f"key insight references invalid claim indices: {invalid}")
        return self
