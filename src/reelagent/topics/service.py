from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session, sessionmaker

from reelagent.config import Settings
from reelagent.persistence import session_scope
from reelagent.topics.discovery import HackerNewsDiscoveryCoordinator
from reelagent.topics.models import TopicCandidate
from reelagent.topics.persistence import SqlAlchemyTopicCandidateRepository


class DiscoveryCoordinator(Protocol):
    async def discover(self) -> list[TopicCandidate]: ...


@dataclass(frozen=True)
class DiscoveryCandidateSummary:
    title: str
    source_kind: str
    external_id: str | None
    points: int
    comment_count: int
    discovery_method: str | None
    matched_topic_group: str | None
    matched_query: str | None


@dataclass(frozen=True)
class DiscoveryRunResult:
    discovered_count: int
    persisted_count: int
    candidates: list[DiscoveryCandidateSummary]


class TopicDiscoveryService:
    """Run discovery and persist the resulting candidate pool."""

    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: sessionmaker[Session],
        coordinator: DiscoveryCoordinator | None = None,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.coordinator = coordinator or HackerNewsDiscoveryCoordinator(settings)

    async def run(self) -> DiscoveryRunResult:
        candidates = await self.coordinator.discover()
        with session_scope(self.session_factory) as session:
            repository = SqlAlchemyTopicCandidateRepository(session)
            persisted_ids = {repository.save(candidate).id for candidate in candidates}

        return DiscoveryRunResult(
            discovered_count=len(candidates),
            persisted_count=len(persisted_ids),
            candidates=[_summarize(candidate) for candidate in candidates],
        )


def _summarize(candidate: TopicCandidate) -> DiscoveryCandidateSummary:
    metadata = candidate.source.metadata
    return DiscoveryCandidateSummary(
        title=candidate.title,
        source_kind=candidate.source.source_kind.value,
        external_id=candidate.source.external_id,
        points=_int_metadata(metadata.get("points")),
        comment_count=_int_metadata(metadata.get("comment_count")),
        discovery_method=_str_metadata(metadata.get("discovery_method")),
        matched_topic_group=_str_metadata(metadata.get("matched_topic_group")),
        matched_query=_str_metadata(metadata.get("matched_query")),
    )


def _int_metadata(value: object) -> int:
    return value if isinstance(value, int) else 0


def _str_metadata(value: object) -> str | None:
    return value if isinstance(value, str) else None
