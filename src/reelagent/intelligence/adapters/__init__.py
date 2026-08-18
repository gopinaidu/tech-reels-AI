"""External adapters for Topic Intelligence."""

from reelagent.intelligence.adapters.hacker_news import HackerNewsEvidenceCollector
from reelagent.intelligence.adapters.openai import (
    OpenAiStructuredLlmClient,
    OpenAiStructuredLlmError,
)

__all__ = [
    "HackerNewsEvidenceCollector",
    "OpenAiStructuredLlmClient",
    "OpenAiStructuredLlmError",
]
