from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from reelagent.topics.models import DiscoveryQuery, SourceEvidence, SourceKind, TopicCandidate


def test_topic_candidate_accepts_timezone_aware_timestamps() -> None:
    published_at = datetime(2026, 8, 8, 10, 0, tzinfo=UTC)
    discovered_at = datetime(2026, 8, 8, 11, 0, tzinfo=UTC)

    source = SourceEvidence(
        source_name="Example Project",
        source_kind=SourceKind.OFFICIAL,
        url="https://example.com/releases/1",
        published_at=published_at,
    )
    candidate = TopicCandidate(
        title="Example release",
        summary="A material software release worth evaluating for reel coverage.",
        discovered_at=discovered_at,
        source=source,
    )

    assert candidate.discovered_at == discovered_at
    assert candidate.source.published_at == published_at


def test_source_evidence_rejects_naive_publication_timestamp() -> None:
    with pytest.raises(ValidationError, match="published_at must be timezone-aware"):
        SourceEvidence(
            source_name="Example Project",
            source_kind=SourceKind.OFFICIAL,
            url="https://example.com/releases/1",
            published_at=datetime(2026, 8, 8, 10, 0),
        )


def test_topic_candidate_rejects_naive_discovery_timestamp() -> None:
    source = SourceEvidence(
        source_name="Example Project",
        source_kind=SourceKind.OFFICIAL,
        url="https://example.com/releases/1",
    )

    with pytest.raises(ValidationError, match="discovered_at must be timezone-aware"):
        TopicCandidate(
            title="Example release",
            summary="A material software release worth evaluating for reel coverage.",
            discovered_at=datetime(2026, 8, 8, 11, 0),
            source=source,
        )


def test_discovery_query_enforces_limit_bounds() -> None:
    with pytest.raises(ValidationError):
        DiscoveryQuery(limit=0)

    with pytest.raises(ValidationError):
        DiscoveryQuery(limit=101)


def test_discovery_query_rejects_naive_since_timestamp() -> None:
    with pytest.raises(ValidationError, match="since must be timezone-aware"):
        DiscoveryQuery(since=datetime(2026, 8, 8, 9, 0))
