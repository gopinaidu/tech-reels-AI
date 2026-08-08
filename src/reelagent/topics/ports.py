from typing import Protocol

from reelagent.topics.models import DiscoveryQuery, TopicCandidate


class TopicDiscoverySource(Protocol):
    """Provider-neutral contract implemented by discovery source adapters."""

    async def discover(self, query: DiscoveryQuery) -> list[TopicCandidate]: ...
