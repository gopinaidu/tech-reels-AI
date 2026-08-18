import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import HttpUrl

from reelagent.intelligence.models import Evidence, EvidenceRole, TopicEvidencePackage
from reelagent.intelligence.service import LlmTopicIntelligenceService, TopicIntelligenceOutputError
from reelagent.topics.models import SourceEvidence, SourceKind, TopicCandidate


def _package(*, injected: bool = False) -> TopicEvidencePackage:
    now = datetime.now(UTC)
    topic = TopicCandidate(
        title="PostgreSQL planner improvement",
        summary="Hacker News story: PostgreSQL planner improvement",
        discovered_at=now,
        source=SourceEvidence(
            source_name="Hacker News",
            source_kind=SourceKind.HACKER_NEWS,
            url=HttpUrl("https://news.ycombinator.com/item?id=123"),
            external_id="123",
            published_at=now,
        ),
    )
    evidence = Evidence(
        evidence_id="hn-story:123",
        source=topic.source,
        roles=frozenset({EvidenceRole.DISCOVERY, EvidenceRole.DISCUSSION}),
        summary="PostgreSQL planner behavior changed for a documented case.",
        retrieved_at=now,
        instruction_like_content_detected=injected,
    )
    return TopicEvidencePackage(topic=topic, evidence=(evidence,))


def _valid_output() -> dict[str, Any]:
    return {
        "what_happened": "A PostgreSQL planner behavior change is being discussed.",
        "why_it_matters": "Planner choices can alter latency for production workloads.",
        "recommended_angle": "Why a planner change can surprise production systems",
        "claims": [
            {
                "text": "A planner behavior change is described in the supplied evidence.",
                "kind": "fact",
                "evidence_ids": ["hn-story:123"],
                "material": True,
                "verification_required": True,
            }
        ],
        "key_insights": [
            {
                "title": "Plans can change",
                "explanation": "Small planner changes can select a different execution strategy.",
                "claim_indices": [0],
            }
        ],
        "discussion_insights": [],
        "reel_worthiness": {
            "novelty": 3,
            "technical_depth": 5,
            "audience_value": 5,
            "visual_explainability": 4,
            "overall_score": 84,
            "rationale": "Strong technical takeaway for senior engineers.",
        },
    }


class _FakeClient:
    def __init__(self, output: dict[str, Any]) -> None:
        self.output = output
        self.last_payload: dict[str, Any] | None = None
        self.last_schema: dict[str, Any] | None = None
        self.last_prompt: str | None = None

    async def generate_json(
        self,
        *,
        system_prompt: str,
        input_payload: dict[str, Any],
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        self.last_prompt = system_prompt
        self.last_payload = input_payload
        self.last_schema = output_schema
        return self.output


def test_generates_brief_and_preserves_authoritative_input() -> None:
    package = _package()
    client = _FakeClient(_valid_output())
    service = LlmTopicIntelligenceService(client)

    brief = asyncio.run(service.analyze(package))

    assert brief.topic == package.topic
    assert brief.evidence == package.evidence
    assert brief.claims[0].evidence_ids == ("hn-story:123",)
    assert client.last_schema is not None
    assert client.last_prompt is not None
    assert "untrusted" in client.last_prompt.lower()


def test_marks_instruction_like_evidence_in_model_payload() -> None:
    client = _FakeClient(_valid_output())
    service = LlmTopicIntelligenceService(client)

    asyncio.run(service.analyze(_package(injected=True)))

    assert client.last_payload is not None
    safety = client.last_payload["safety"]
    assert safety["retrieved_content_is_untrusted"] is True
    assert safety["instruction_like_evidence_ids"] == ["hn-story:123"]


def test_rejects_unknown_evidence_reference_from_model() -> None:
    output = _valid_output()
    output["claims"][0]["evidence_ids"] = ["invented-source"]
    service = LlmTopicIntelligenceService(_FakeClient(output))

    with pytest.raises(TopicIntelligenceOutputError, match="invalid structured output"):
        asyncio.run(service.analyze(_package()))


def test_rejects_malformed_model_output() -> None:
    service = LlmTopicIntelligenceService(_FakeClient({"what_happened": "Incomplete"}))

    with pytest.raises(TopicIntelligenceOutputError, match="invalid structured output"):
        asyncio.run(service.analyze(_package()))
