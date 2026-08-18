from datetime import UTC, datetime

import pytest
from pydantic import HttpUrl, ValidationError

from reelagent.intelligence.models import (
    Claim,
    ClaimKind,
    DiscussionInsight,
    DiscussionInsightKind,
    Evidence,
    EvidenceRole,
    KeyInsight,
    ReelWorthiness,
    TopicBrief,
    TopicEvidencePackage,
)
from reelagent.topics.models import SourceEvidence, SourceKind, TopicCandidate


def _topic() -> TopicCandidate:
    now = datetime.now(UTC)
    return TopicCandidate(
        title="PostgreSQL query planner improvement",
        summary="A PostgreSQL query planner improvement is being discussed.",
        discovered_at=now,
        source=SourceEvidence(
            source_name="Hacker News",
            source_kind=SourceKind.HACKER_NEWS,
            url=HttpUrl("https://news.ycombinator.com/item?id=123"),
            external_id="123",
            published_at=now,
            metadata={"points": 120, "comment_count": 35},
        ),
    )


def _evidence(evidence_id: str = "official-release") -> Evidence:
    now = datetime.now(UTC)
    return Evidence(
        evidence_id=evidence_id,
        source=SourceEvidence(
            source_name="PostgreSQL",
            source_kind=SourceKind.OFFICIAL,
            url=HttpUrl("https://www.postgresql.org/docs/current/"),
            published_at=now,
        ),
        roles=frozenset({EvidenceRole.VERIFICATION}),
        summary="Official PostgreSQL documentation supporting the planner behavior.",
        retrieved_at=now,
    )


def _worthiness() -> ReelWorthiness:
    return ReelWorthiness(
        novelty=4,
        technical_depth=5,
        audience_value=5,
        visual_explainability=3,
        overall_score=86,
        rationale="Strong architecture relevance with a concrete technical takeaway.",
    )


def test_factual_claim_requires_evidence() -> None:
    with pytest.raises(ValidationError, match="factual claims must reference"):
        Claim(text="The planner changed.", kind=ClaimKind.FACT)


def test_evidence_package_rejects_duplicate_ids() -> None:
    evidence = _evidence()

    with pytest.raises(ValidationError, match="evidence_id values must be unique"):
        TopicEvidencePackage(topic=_topic(), evidence=(evidence, evidence))


def test_topic_brief_rejects_unknown_evidence_reference() -> None:
    with pytest.raises(ValidationError, match="unknown evidence ids"):
        TopicBrief(
            topic=_topic(),
            what_happened="PostgreSQL changed planner behavior.",
            why_it_matters="Planner choices can materially affect production query latency.",
            recommended_angle="Why a small planner change can alter production performance",
            claims=(
                Claim(
                    text="The planner behavior changed.",
                    kind=ClaimKind.FACT,
                    evidence_ids=("missing",),
                ),
            ),
            key_insights=(
                KeyInsight(
                    title="Planner choices matter",
                    explanation="Cost estimates can change the selected execution strategy.",
                    claim_indices=(0,),
                ),
            ),
            evidence=(_evidence(),),
            reel_worthiness=_worthiness(),
            created_at=datetime.now(UTC),
        )


def test_topic_brief_accepts_auditable_cross_references() -> None:
    evidence = _evidence()
    brief = TopicBrief(
        topic=_topic(),
        what_happened="PostgreSQL changed planner behavior.",
        why_it_matters="Planner choices can materially affect production query latency.",
        recommended_angle="Why a small planner change can alter production performance",
        claims=(
            Claim(
                text="The documented planner behavior changed.",
                kind=ClaimKind.FACT,
                evidence_ids=(evidence.evidence_id,),
            ),
            Claim(
                text=(
                    "Teams should benchmark representative production queries "
                    "before upgrading."
                ),
                kind=ClaimKind.RECOMMENDATION,
                verification_required=False,
            ),
        ),
        key_insights=(
            KeyInsight(
                title="Planner choices matter",
                explanation="A planner improvement can change execution strategy and latency.",
                claim_indices=(0, 1),
            ),
        ),
        discussion_insights=(
            DiscussionInsight(
                kind=DiscussionInsightKind.PRACTICAL_EXPERIENCE,
                summary="Practitioners are comparing planner outcomes on real workloads.",
                evidence_ids=(evidence.evidence_id,),
            ),
        ),
        evidence=(evidence,),
        reel_worthiness=_worthiness(),
        created_at=datetime.now(UTC),
    )

    assert brief.claims[0].evidence_ids == ("official-release",)
    assert brief.reel_worthiness.overall_score == 86


def test_topic_brief_requires_timezone_aware_created_at() -> None:
    evidence = _evidence()

    with pytest.raises(ValidationError, match="created_at must be timezone-aware"):
        TopicBrief(
            topic=_topic(),
            what_happened="PostgreSQL changed planner behavior.",
            why_it_matters="Planner choices can affect query latency.",
            recommended_angle="Why planner changes matter",
            claims=(
                Claim(
                    text="The planner behavior changed.",
                    kind=ClaimKind.FACT,
                    evidence_ids=(evidence.evidence_id,),
                ),
            ),
            key_insights=(
                KeyInsight(
                    title="Planner choices matter",
                    explanation="Execution strategies can change.",
                    claim_indices=(0,),
                ),
            ),
            evidence=(evidence,),
            reel_worthiness=_worthiness(),
            created_at=datetime(2026, 8, 18),
        )
