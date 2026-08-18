from typing import Protocol

from reelagent.intelligence.models import TopicBrief, TopicEvidencePackage


class TopicIntelligenceService(Protocol):
    """Turn bounded topic evidence into a structured, auditable Topic Brief."""

    async def analyze(self, evidence_package: TopicEvidencePackage) -> TopicBrief:
        """Analyze one topic without performing unrelated workflow side effects."""
        ...
