from datetime import datetime, timezone

from pydantic import HttpUrl
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from reelagent.persistence import Base
from reelagent.topics.models import SourceEvidence, SourceKind, TopicCandidate
from reelagent.topics.persistence import (
    SqlAlchemyTopicCandidateRepository,
    build_dedupe_key,
    normalize_title,
)


def candidate(*, source_name: str, source_kind: SourceKind, url: str, external_id: str) -> TopicCandidate:
    now = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
    return TopicCandidate(
        title="  Kafka 4.2   Queue Semantics ",
        summary="A useful engineering topic.",
        discovered_at=now,
        source=SourceEvidence(
            source_name=source_name,
            source_kind=source_kind,
            url=HttpUrl(url),
            external_id=external_id,
            published_at=now,
        ),
    )


def test_normalize_title_is_case_and_whitespace_insensitive() -> None:
    assert normalize_title("  Kafka   Queues ") == "kafka queues"


def test_dedupe_key_is_source_neutral() -> None:
    hn = candidate(
        source_name="Hacker News",
        source_kind=SourceKind.HACKER_NEWS,
        url="https://news.ycombinator.com/item?id=1",
        external_id="1",
    )
    official = candidate(
        source_name="Apache Kafka",
        source_kind=SourceKind.OFFICIAL,
        url="https://kafka.apache.org/release-notes",
        external_id="release-4.2",
    )

    assert build_dedupe_key(hn) == build_dedupe_key(official)


def test_repository_merges_sources_for_same_normalized_topic() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    hn = candidate(
        source_name="Hacker News",
        source_kind=SourceKind.HACKER_NEWS,
        url="https://news.ycombinator.com/item?id=1",
        external_id="1",
    )
    official = candidate(
        source_name="Apache Kafka",
        source_kind=SourceKind.OFFICIAL,
        url="https://kafka.apache.org/release-notes",
        external_id="release-4.2",
    )

    with Session(engine) as session:
        repository = SqlAlchemyTopicCandidateRepository(session)
        first = repository.save(hn)
        second = repository.save(official)
        session.commit()

        assert first.id == second.id
        assert len(second.sources) == 2


def test_repository_does_not_duplicate_same_source() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    hn = candidate(
        source_name="Hacker News",
        source_kind=SourceKind.HACKER_NEWS,
        url="https://news.ycombinator.com/item?id=1",
        external_id="1",
    )

    with Session(engine) as session:
        repository = SqlAlchemyTopicCandidateRepository(session)
        repository.save(hn)
        row = repository.save(hn)
        session.commit()

        assert len(row.sources) == 1
