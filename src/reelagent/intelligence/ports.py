from typing import Protocol

from reelagent.intelligence.models import TopicBrief, TopicEvidencePackage
from reelagent.topics.models import TopicCandidate


class TopicEvidenceCollector(Protocol):
    """Collect bounded, auditable evidence for one discovered topic."""

    async def collect(self, topic: TopicCandidate) -> TopicEvidencePackage:
        """Collect evidence without performing analysis or unrelated workflow side effects."""
        ...


class TopicIntelligenceService(Protocol):
    """Turn bounded topic evidence into a structured, auditable Topic Brief."""

    async def analyze(self, evidence_package: TopicEvidencePackage) -> TopicBrief:
        """Analyze one topic without performing unrelated workflow side effects."""
        ...
