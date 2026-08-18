from typing import Any, Protocol

from reelagent.intelligence.models import TopicBrief, TopicEvidencePackage
from reelagent.topics.models import TopicCandidate


class TopicEvidenceCollector(Protocol):
    """Collect bounded, auditable evidence for one discovered topic."""

    async def collect(self, topic: TopicCandidate) -> TopicEvidencePackage:
        """Collect evidence without performing analysis or unrelated workflow side effects."""
        ...


class StructuredLlmClient(Protocol):
    """Provider-neutral client for one schema-constrained model generation."""

    async def generate_json(
        self,
        *,
        system_prompt: str,
        input_payload: dict[str, Any],
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Return one JSON object matching the requested schema or raise on provider failure."""
        ...


class TopicIntelligenceService(Protocol):
    """Turn bounded topic evidence into a structured, auditable Topic Brief."""

    async def analyze(self, evidence_package: TopicEvidencePackage) -> TopicBrief:
        """Analyze one topic without performing unrelated workflow side effects."""
        ...
