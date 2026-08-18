import asyncio
from datetime import UTC, datetime

from pydantic import HttpUrl

from reelagent.intelligence.models import (
    Claim,
    ClaimKind,
    Evidence,
    EvidenceRole,
    KeyInsight,
    ReelWorthiness,
    TopicBrief,
    TopicEvidencePackage,
)
from reelagent.intelligence.pipeline import TopicIntelligencePipeline
from reelagent.intelligence.quality import TopicQualityDecision, TopicQualityGate
from reelagent.topics.models import SourceEvidence, SourceKind, TopicCandidate


def _topic() -> TopicCandidate:
    now = datetime.now(UTC)
    source = SourceEvidence(
        source_name="Hacker News",
        source_kind=SourceKind.HACKER_NEWS,
        url=HttpUrl("https://news.ycombinator.com/item?id=123"),
        external_id="123",
        published_at=now,
    )
    return TopicCandidate(
        title="PostgreSQL planner improvement",
        summary="HN story about a PostgreSQL planner improvement.",
        discovered_at=now,
        source=source,
    )


def _package(*, injected: bool = False) -> TopicEvidencePackage:
    topic = _topic()
    evidence = Evidence(
        evidence_id="hn-story:123",
        source=topic.source,
        roles=frozenset({EvidenceRole.DISCOVERY, EvidenceRole.DISCUSSION}),
        summary="The story describes a planner behavior change.",
        retrieved_at=datetime.now(UTC),
        instruction_like_content_detected=injected,
    )
    return TopicEvidencePackage(topic=topic, evidence=(evidence,))


def _brief(package: TopicEvidencePackage, *, score: int = 80) -> TopicBrief:
    return TopicBrief(
        topic=package.topic,
        what_happened="A planner behavior change is being discussed.",
        why_it_matters="Planner choices can affect production latency.",
        recommended_angle="Why planner changes can surprise production systems",
        claims=(
            Claim(
                text="The supplied evidence describes a planner behavior change.",
                kind=ClaimKind.FACT,
                evidence_ids=("hn-story:123",),
                material=True,
                verification_required=True,
            ),
        ),
        key_insights=(
            KeyInsight(
                title="Plans can change",
                explanation="Small planner changes can alter execution strategy.",
                claim_indices=(0,),
            ),
        ),
        evidence=package.evidence,
        reel_worthiness=ReelWorthiness(
            novelty=3,
            technical_depth=5,
            audience_value=5,
            visual_explainability=4,
            overall_score=score,
            rationale="Useful technical lesson.",
        ),
        created_at=datetime.now(UTC),
    )


class _Collector:
    def __init__(self, package: TopicEvidencePackage) -> None:
        self.package = package

    async def collect(self, topic: TopicCandidate) -> TopicEvidencePackage:
        assert topic == self.package.topic
        return self.package


class _IntelligenceService:
    def __init__(self, brief: TopicBrief) -> None:
        self.brief = brief

    async def analyze(self, evidence_package: TopicEvidencePackage) -> TopicBrief:
        assert evidence_package.evidence == self.brief.evidence
        return self.brief


def test_pipeline_runs_collection_analysis_and_quality_gate() -> None:
    package = _package()
    pipeline = TopicIntelligencePipeline(
        evidence_collector=_Collector(package),
        intelligence_service=_IntelligenceService(_brief(package)),
        quality_gate=TopicQualityGate(min_reel_worthiness_score=65),
    )

    result = asyncio.run(pipeline.run(package.topic))

    assert result.quality.decision == TopicQualityDecision.READY_FOR_VERIFICATION
    assert result.quality.claims_requiring_independent_verification == (0,)


def test_quality_gate_rejects_low_value_topic() -> None:
    package = _package()
    result = TopicQualityGate(min_reel_worthiness_score=65).evaluate(
        _brief(package, score=40)
    )

    assert result.decision == TopicQualityDecision.REJECTED
    assert "reel worthiness" in result.reasons[0]


def test_quality_gate_rejects_claim_using_instruction_like_evidence() -> None:
    package = _package(injected=True)
    result = TopicQualityGate().evaluate(_brief(package))

    assert result.decision == TopicQualityDecision.REJECTED
    assert any("instruction-like evidence" in reason for reason in result.reasons)
