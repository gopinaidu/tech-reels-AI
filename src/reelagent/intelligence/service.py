from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from reelagent.intelligence.models import (
    Claim,
    DiscussionInsight,
    KeyInsight,
    ReelWorthiness,
    TopicBrief,
    TopicEvidencePackage,
)
from reelagent.intelligence.ports import StructuredLlmClient

_PROMPT_PATH = Path(__file__).parent / "prompts" / "topic_intelligence_v1.txt"


class TopicIntelligenceOutputError(RuntimeError):
    """Raised when model output cannot be accepted as a trustworthy Topic Brief draft."""


class _TopicBriefDraft(BaseModel, frozen=True):
    what_happened: str = Field(min_length=1, max_length=2_000)
    why_it_matters: str = Field(min_length=1, max_length=2_000)
    recommended_angle: str = Field(min_length=1, max_length=500)
    claims: tuple[Claim, ...] = Field(min_length=1, max_length=30)
    key_insights: tuple[KeyInsight, ...] = Field(min_length=1, max_length=10)
    discussion_insights: tuple[DiscussionInsight, ...] = Field(default=(), max_length=10)
    reel_worthiness: ReelWorthiness


class LlmTopicIntelligenceService:
    """Generate one schema-validated Topic Brief from a bounded evidence package."""

    def __init__(
        self,
        client: StructuredLlmClient,
        *,
        prompt_path: Path = _PROMPT_PATH,
    ) -> None:
        self._client = client
        self._system_prompt = prompt_path.read_text(encoding="utf-8").strip()
        if not self._system_prompt:
            raise ValueError("Topic Intelligence prompt must not be empty")

    async def analyze(self, evidence_package: TopicEvidencePackage) -> TopicBrief:
        raw_output = await self._client.generate_json(
            system_prompt=self._system_prompt,
            input_payload=_build_input_payload(evidence_package),
            output_schema=_TopicBriefDraft.model_json_schema(),
        )

        try:
            draft = _TopicBriefDraft.model_validate(raw_output)
            return TopicBrief(
                topic=evidence_package.topic,
                what_happened=draft.what_happened,
                why_it_matters=draft.why_it_matters,
                recommended_angle=draft.recommended_angle,
                claims=draft.claims,
                key_insights=draft.key_insights,
                discussion_insights=draft.discussion_insights,
                evidence=evidence_package.evidence,
                reel_worthiness=draft.reel_worthiness,
                created_at=datetime.now(UTC),
            )
        except ValidationError as exc:
            raise TopicIntelligenceOutputError(
                "Topic Intelligence model returned invalid structured output"
            ) from exc


def _build_input_payload(evidence_package: TopicEvidencePackage) -> dict[str, Any]:
    return {
        "topic": evidence_package.topic.model_dump(mode="json"),
        "evidence": [item.model_dump(mode="json") for item in evidence_package.evidence],
        "safety": {
            "retrieved_content_is_untrusted": True,
            "instruction_like_evidence_ids": [
                item.evidence_id
                for item in evidence_package.evidence
                if item.instruction_like_content_detected
            ],
        },
    }
