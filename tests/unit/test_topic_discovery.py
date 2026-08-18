import asyncio
from datetime import UTC, datetime

from pydantic import HttpUrl

import reelagent.topics.discovery as discovery_module
from reelagent.config import Settings
from reelagent.topics.discovery import HackerNewsDiscoveryCoordinator
from reelagent.topics.models import DiscoveryQuery, SourceEvidence, SourceKind, TopicCandidate


def _candidate(
    title: str,
    *,
    external_id: str,
    points: int,
    comments: int,
    discovery_method: str,
    matched_topic_group: str | None = None,
    matched_query: str | None = None,
    summary: str | None = None,
) -> TopicCandidate:
    metadata: dict[str, object] = {
        "points": points,
        "comment_count": comments,
        "discovery_method": discovery_method,
    }
    if matched_topic_group is not None:
        metadata["matched_topic_group"] = matched_topic_group
    if matched_query is not None:
        metadata["matched_query"] = matched_query

    now = datetime.now(UTC)
    return TopicCandidate(
        title=title,
        summary=summary or f"Hacker News story: {title}",
        discovered_at=now,
        source=SourceEvidence(
            source_name="Hacker News",
            source_kind=SourceKind.HACKER_NEWS,
            url=HttpUrl(f"https://news.ycombinator.com/item?id={external_id}"),
            external_id=external_id,
            published_at=now,
            metadata=metadata,
        ),
    )


class _FakeTrendingSource:
    def __init__(self, candidates: list[TopicCandidate]) -> None:
        self.candidates = candidates

    async def discover(self, query: DiscoveryQuery) -> list[TopicCandidate]:
        return self.candidates[: query.limit]


def test_coordinator_filters_irrelevant_trending_and_ranks_technical_topics() -> None:
    trending = [
        _candidate(
            "Being ambitious and being a dad",
            external_id="1",
            points=900,
            comments=500,
            discovery_method="trending",
        ),
        _candidate(
            "Linux kernel improves GPU memory performance",
            external_id="2",
            points=120,
            comments=30,
            discovery_method="trending",
        ),
        _candidate(
            "Rust vector database gets faster indexing",
            external_id="3",
            points=80,
            comments=20,
            discovery_method="trending",
        ),
    ]
    settings = Settings(
        _env_file=None,
        discovery_topic_groups={},
        hn_trending_limit=20,
        hn_discovery_limit=10,
    )
    coordinator = HackerNewsDiscoveryCoordinator(
        settings,
        trending_source=_FakeTrendingSource(trending),
    )

    result = asyncio.run(coordinator.discover())

    assert [candidate.title for candidate in result] == [
        "Linux kernel improves GPU memory performance",
        "Rust vector database gets faster indexing",
    ]


def test_targeted_and_trending_candidates_share_one_ranked_pool(monkeypatch) -> None:
    trending = [
        _candidate(
            "Linux kernel performance improvements",
            external_id="10",
            points=100,
            comments=25,
            discovery_method="trending",
        )
    ]
    targeted = [
        _candidate(
            "Kafka event processing reliability lessons",
            external_id="20",
            points=70,
            comments=40,
            discovery_method="targeted_search",
            matched_topic_group="streaming",
            matched_query="Kafka",
        )
    ]

    class _FakeSearchSource:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def discover(self, query: DiscoveryQuery) -> list[TopicCandidate]:
            return targeted[: query.limit]

    monkeypatch.setattr(discovery_module, "HackerNewsSearchSource", _FakeSearchSource)
    settings = Settings(
        _env_file=None,
        discovery_topic_groups={"streaming": ("Kafka",)},
        hn_trending_limit=20,
        hn_targeted_limit_per_query=5,
        hn_discovery_limit=10,
    )
    coordinator = HackerNewsDiscoveryCoordinator(
        settings,
        trending_source=_FakeTrendingSource(trending),
    )

    result = asyncio.run(coordinator.discover())

    assert [candidate.title for candidate in result] == [
        "Linux kernel performance improvements",
        "Kafka event processing reliability lessons",
    ]


def test_deduplication_keeps_higher_scored_candidate(monkeypatch) -> None:
    trending = [
        _candidate(
            "PostgreSQL query planner deep dive",
            external_id="30",
            points=200,
            comments=60,
            discovery_method="trending",
        )
    ]
    targeted = [
        _candidate(
            "PostgreSQL query planner deep dive",
            external_id="30",
            points=200,
            comments=60,
            discovery_method="targeted_search",
            matched_topic_group="data",
            matched_query="PostgreSQL",
        )
    ]

    class _FakeSearchSource:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def discover(self, query: DiscoveryQuery) -> list[TopicCandidate]:
            return targeted[: query.limit]

    monkeypatch.setattr(discovery_module, "HackerNewsSearchSource", _FakeSearchSource)
    settings = Settings(
        _env_file=None,
        discovery_topic_groups={"data": ("PostgreSQL",)},
        hn_discovery_limit=10,
    )
    coordinator = HackerNewsDiscoveryCoordinator(
        settings,
        trending_source=_FakeTrendingSource(trending),
    )

    result = asyncio.run(coordinator.discover())

    assert len(result) == 1
    assert result[0].source.metadata["discovery_method"] == "targeted_search"


def test_synthetic_summary_does_not_inflate_title_relevance() -> None:
    candidate = _candidate(
        "A practical field guide",
        external_id="40",
        points=20,
        comments=10,
        discovery_method="targeted_search",
        matched_topic_group="ai",
        matched_query="AI agent",
        summary="Hacker News story matching AI agent, LLM, RAG, Python, Kafka, Kubernetes",
    )

    assert discovery_module._title_relevance(candidate) == 0
    assert discovery_module._is_technically_relevant(candidate) is True


def test_weighted_score_allows_engagement_to_overcome_one_keyword_difference() -> None:
    low_engagement = _candidate(
        "Linux kernel GPU performance",
        external_id="50",
        points=10,
        comments=2,
        discovery_method="trending",
    )
    high_engagement = _candidate(
        "PostgreSQL performance breakthrough",
        external_id="51",
        points=500,
        comments=250,
        discovery_method="trending",
    )

    assert discovery_module._title_relevance(low_engagement) > discovery_module._title_relevance(
        high_engagement
    )
    assert discovery_module._candidate_score(high_engagement) > discovery_module._candidate_score(
        low_engagement
    )
