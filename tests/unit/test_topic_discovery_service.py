import asyncio
from datetime import UTC, datetime

from pydantic import HttpUrl
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from reelagent.config import Settings
from reelagent.persistence import Base, create_session_factory
from reelagent.topics.models import SourceEvidence, SourceKind, TopicCandidate
from reelagent.topics.persistence import TopicCandidateRow, TopicSourceRow
from reelagent.topics.service import TopicDiscoveryService


class FakeCoordinator:
    def __init__(self, candidates: list[TopicCandidate]) -> None:
        self.candidates = candidates

    async def discover(self) -> list[TopicCandidate]:
        return self.candidates


def _candidate() -> TopicCandidate:
    now = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
    return TopicCandidate(
        title="PostgreSQL performance improvements",
        summary="Hacker News story matching PostgreSQL.",
        discovered_at=now,
        source=SourceEvidence(
            source_name="Hacker News",
            source_kind=SourceKind.HACKER_NEWS,
            url=HttpUrl("https://news.ycombinator.com/item?id=123"),
            external_id="123",
            published_at=now,
            metadata={
                "points": 42,
                "comment_count": 11,
                "discovery_method": "targeted_search",
                "matched_topic_group": "data",
                "matched_query": "PostgreSQL",
            },
        ),
    )


def test_discovery_service_persists_and_summarizes_candidates() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    service = TopicDiscoveryService(
        settings=Settings(),
        session_factory=create_session_factory(engine),
        coordinator=FakeCoordinator([_candidate()]),
    )

    result = asyncio.run(service.run())

    assert result.discovered_count == 1
    assert result.persisted_count == 1
    assert result.candidates[0].title == "PostgreSQL performance improvements"
    assert result.candidates[0].points == 42
    assert result.candidates[0].comment_count == 11
    assert result.candidates[0].matched_topic_group == "data"
    assert result.candidates[0].matched_query == "PostgreSQL"


def test_repeated_discovery_does_not_duplicate_candidate_or_source() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    service = TopicDiscoveryService(
        settings=Settings(),
        session_factory=create_session_factory(engine),
        coordinator=FakeCoordinator([_candidate()]),
    )

    asyncio.run(service.run())
    asyncio.run(service.run())

    with Session(engine) as session:
        candidate_count = session.scalar(select(func.count()).select_from(TopicCandidateRow))
        source_count = session.scalar(select(func.count()).select_from(TopicSourceRow))

    assert candidate_count == 1
    assert source_count == 1
