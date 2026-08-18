"""Topic Intelligence domain contracts and application services."""

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
from reelagent.intelligence.pipeline import (
    TopicIntelligencePipeline,
    TopicIntelligencePipelineResult,
)
from reelagent.intelligence.ports import (
    StructuredLlmClient,
    TopicEvidenceCollector,
    TopicIntelligenceService,
)
from reelagent.intelligence.quality import (
    TopicQualityDecision,
    TopicQualityGate,
    TopicQualityResult,
)
from reelagent.intelligence.service import (
    LlmTopicIntelligenceService,
    TopicIntelligenceOutputError,
)

__all__ = [
    "Claim",
    "ClaimKind",
    "DiscussionInsight",
    "DiscussionInsightKind",
    "Evidence",
    "EvidenceRole",
    "KeyInsight",
    "LlmTopicIntelligenceService",
    "ReelWorthiness",
    "StructuredLlmClient",
    "TopicBrief",
    "TopicEvidenceCollector",
    "TopicEvidencePackage",
    "TopicIntelligenceOutputError",
    "TopicIntelligencePipeline",
    "TopicIntelligencePipelineResult",
    "TopicIntelligenceService",
    "TopicQualityDecision",
    "TopicQualityGate",
    "TopicQualityResult",
]
