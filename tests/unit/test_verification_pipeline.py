import asyncio
from datetime import UTC, datetime

import pytest
from pydantic import HttpUrl

from reelagent.intelligence.models import (
    Claim,
    ClaimKind,
    Evidence,
    EvidenceRole,
    KeyInsight,
    ReelWorthiness,
    TopicBrief,
)
from reelagent.intelligence.quality import TopicQualityDecision, TopicQualityResult
from reelagent.topics.models import SourceEvidence, SourceKind, TopicCandidate
from reelagent.verification.models import (
    ClaimVerificationRequest,
    ClaimVerificationResult,
    ClaimVerificationVerdict,
    VerificationOutcome,
)
from reelagent.verification.pipeline import VerificationPipeline


def _evidence(evidence_id: str, kind: SourceKind, url: str) -> Evidence:
    now = datetime.now(UTC)
    return Evidence(
        evidence_id=evidence_id,
        source=SourceEvidence(
            source_name=evidence_id,
            source_kind=kind,
            url=HttpUrl(url),
            published_at=now,
        ),
        roles=frozenset({EvidenceRole.VERIFICATION}),
        summary="Evidence relevant to the claim.",
        retrieved_at=now,
    )


def _brief() -> TopicBrief:
    now = datetime.now(UTC)
    discovery = _evidence(
        "hn-story:123",
        SourceKind.HACKER_NEWS,
        "https://news.ycombinator.com/item?id=123",
    )
    topic = TopicCandidate(
        title="PostgreSQL queue discussion",
        summary="A PostgreSQL queue technique is being discussed.",
        discovered_at=now,
        source=discovery.source,
    )
    return TopicBrief(
        topic=topic,
        what_happened="A PostgreSQL queue technique is being discussed.",
        why_it_matters="It may reduce infrastructure for some workloads.",
        recommended_angle="When Postgres can replace a dedicated queue",
        claims=(
            Claim(
                text="PostgreSQL supports SKIP LOCKED for worker coordination.",
                kind=ClaimKind.FACT,
                evidence_ids=(discovery.evidence_id,),
            ),
        ),
        key_insights=(
            KeyInsight(
                title="Use existing primitives first",
                explanation="A database primitive can sometimes avoid another service.",
                claim_indices=(0,),
            ),
        ),
        evidence=(discovery,),
        reel_worthiness=ReelWorthiness(
            novelty=4,
            technical_depth=5,
            audience_value=5,
            visual_explainability=4,
            overall_score=88,
            rationale="Strong senior-engineering tradeoff.",
        ),
        created_at=now,
    )


def _quality() -> TopicQualityResult:
    return TopicQualityResult(
        decision=TopicQualityDecision.READY_FOR_VERIFICATION,
        claims_requiring_independent_verification=(0,),
    )


class _Collector:
    def __init__(self, evidence: tuple[Evidence, ...]) -> None:
        self.evidence = evidence

    async def collect(self, request: ClaimVerificationRequest) -> tuple[Evidence, ...]:
        return self.evidence


class _Verifier:
    def __init__(self, verdict: ClaimVerificationVerdict) -> None:
        self.verdict = verdict
        self.calls = 0

    async def verify(
        self,
        request: ClaimVerificationRequest,
        evidence: tuple[Evidence, ...],
    ) -> ClaimVerificationResult:
        self.calls += 1
        return ClaimVerificationResult(
            request=request,
            verdict=self.verdict,
            verification_evidence=evidence,
            rationale="Independent evidence was evaluated against the claim.",
        )


def test_supported_claim_is_ready_for_script() -> None:
    official = _evidence(
        "postgres-docs",
        SourceKind.OFFICIAL,
        "https://www.postgresql.org/docs/current/sql-select.html",
    )
    verifier = _Verifier(ClaimVerificationVerdict.SUPPORTED)
    pipeline = VerificationPipeline(
        evidence_collector=_Collector((official,)), verifier=verifier
    )

    report = asyncio.run(pipeline.run(_brief(), _quality()))

    assert report.outcome == VerificationOutcome.READY_FOR_SCRIPT
    assert report.results[0].verification_evidence == (official,)
    assert verifier.calls == 1


def test_community_only_evidence_needs_research() -> None:
    community = _evidence(
        "community-post", SourceKind.COMMUNITY, "https://example.com/community/post"
    )
    verifier = _Verifier(ClaimVerificationVerdict.SUPPORTED)
    pipeline = VerificationPipeline(
        evidence_collector=_Collector((community,)), verifier=verifier
    )

    report = asyncio.run(pipeline.run(_brief(), _quality()))

    assert report.outcome == VerificationOutcome.NEEDS_RESEARCH
    assert verifier.calls == 0


def test_unsupported_claim_requests_revision() -> None:
    official = _evidence(
        "postgres-docs",
        SourceKind.OFFICIAL,
        "https://www.postgresql.org/docs/current/sql-select.html",
    )
    pipeline = VerificationPipeline(
        evidence_collector=_Collector((official,)),
        verifier=_Verifier(ClaimVerificationVerdict.UNSUPPORTED),
    )

    report = asyncio.run(pipeline.run(_brief(), _quality()))

    assert report.outcome == VerificationOutcome.REVISION_REQUIRED


def test_rejects_brief_that_did_not_pass_quality_gate() -> None:
    rejected = TopicQualityResult(
        decision=TopicQualityDecision.REJECTED, reasons=("too weak",)
    )
    pipeline = VerificationPipeline(
        evidence_collector=_Collector(()),
        verifier=_Verifier(ClaimVerificationVerdict.SUPPORTED),
    )

    with pytest.raises(ValueError, match="passed the quality gate"):
        asyncio.run(pipeline.run(_brief(), rejected))
