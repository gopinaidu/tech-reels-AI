from __future__ import annotations

from pydantic import BaseModel

from reelagent.intelligence.models import TopicBrief, TopicEvidencePackage
from reelagent.intelligence.ports import TopicEvidenceCollector, TopicIntelligenceService
from reelagent.intelligence.quality import TopicQualityGate, TopicQualityResult
from reelagent.topics.models import TopicCandidate


class TopicIntelligencePipelineResult(BaseModel, frozen=True):
    evidence_package: TopicEvidencePackage
    brief: TopicBrief
    quality: TopicQualityResult


class TopicIntelligencePipeline:
    """Orchestrate evidence collection, analysis, and deterministic quality review."""

    def __init__(
        self,
        *,
        evidence_collector: TopicEvidenceCollector,
        intelligence_service: TopicIntelligenceService,
        quality_gate: TopicQualityGate,
    ) -> None:
        self._evidence_collector = evidence_collector
        self._intelligence_service = intelligence_service
        self._quality_gate = quality_gate

    async def run(self, topic: TopicCandidate) -> TopicIntelligencePipelineResult:
        evidence_package = await self._evidence_collector.collect(topic)
        brief = await self._intelligence_service.analyze(evidence_package)
        quality = self._quality_gate.evaluate(brief)
        return TopicIntelligencePipelineResult(
            evidence_package=evidence_package,
            brief=brief,
            quality=quality,
        )
