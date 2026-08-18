from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime, timedelta

from reelagent.config import Settings
from reelagent.topics.adapters.hacker_news import HackerNewsDiscoverySource
from reelagent.topics.adapters.hacker_news_search import HackerNewsSearchSource
from reelagent.topics.models import DiscoveryQuery, TopicCandidate
from reelagent.topics.persistence import build_dedupe_key

_TECHNICAL_SIGNALS = (
    "ai",
    "llm",
    "agent",
    "inference",
    "rag",
    "machine learning",
    "model",
    "openai",
    "claude",
    "cursor",
    "software",
    "developer",
    "programming",
    "code",
    "github",
    "git",
    "linux",
    "kernel",
    "database",
    "postgres",
    "postgresql",
    "mongodb",
    "redis",
    "vector",
    "kafka",
    "streaming",
    "flink",
    "java",
    "python",
    "rust",
    "golang",
    "jvm",
    "kubernetes",
    "docker",
    "aws",
    "azure",
    "gcp",
    "cloud",
    "serverless",
    "distributed",
    "microservices",
    "backend",
    "api",
    "system design",
    "scalability",
    "reliability",
    "performance",
    "cpu",
    "gpu",
    "compiler",
)

_RELEVANCE_WEIGHT = 100.0
_TARGETED_SOURCE_BONUS = 25.0
_POINT_WEIGHT = 0.5
_COMMENT_WEIGHT = 1.0
_MAX_POINTS_CONTRIBUTION = 500
_MAX_COMMENTS_CONTRIBUTION = 250


class HackerNewsDiscoveryCoordinator:
    """Combine and rank broad HN trending discovery with configured targeted searches."""

    def __init__(
        self,
        settings: Settings,
        *,
        trending_source: HackerNewsDiscoverySource | None = None,
    ) -> None:
        self.settings = settings
        self.trending_source = trending_source or HackerNewsDiscoverySource()

    async def discover(self) -> list[TopicCandidate]:
        since = datetime.now(UTC) - timedelta(days=self.settings.hn_targeted_freshness_days)
        trending: list[TopicCandidate] = []
        if self.settings.hn_trending_limit:
            trending = await self.trending_source.discover(
                DiscoveryQuery(limit=self.settings.hn_trending_limit, since=since)
            )

        semaphore = asyncio.Semaphore(self.settings.hn_targeted_max_concurrency)

        async def run_targeted(group: str, term: str) -> list[TopicCandidate]:
            source = HackerNewsSearchSource(
                search_term=term,
                topic_group=group,
                min_points=self.settings.hn_targeted_min_points,
                min_comments=self.settings.hn_targeted_min_comments,
            )
            async with semaphore:
                return await source.discover(
                    DiscoveryQuery(
                        limit=self.settings.hn_targeted_limit_per_query,
                        since=since,
                    )
                )

        tasks = [
            run_targeted(group, term)
            for group, terms in self.settings.discovery_topic_groups.items()
            for term in terms
        ]
        targeted_sets = await asyncio.gather(*tasks) if tasks else []
        targeted = sorted(
            (candidate for candidates in targeted_sets for candidate in candidates),
            key=_candidate_score,
            reverse=True,
        )[: self.settings.hn_targeted_total_limit]

        candidates_by_key: dict[str, TopicCandidate] = {}
        for candidate in [*trending, *targeted]:
            if not _is_technically_relevant(candidate):
                continue

            key = build_dedupe_key(candidate)
            existing = candidates_by_key.get(key)
            if existing is None or _candidate_score(candidate) > _candidate_score(existing):
                candidates_by_key[key] = candidate

        ranked = sorted(candidates_by_key.values(), key=_candidate_score, reverse=True)
        return ranked[: self.settings.hn_discovery_limit]


def _title_relevance(candidate: TopicCandidate) -> int:
    title = candidate.title.casefold()
    return sum(
        1 for signal in _TECHNICAL_SIGNALS if re.search(rf"\b{re.escape(signal)}\b", title)
    )


def _is_technically_relevant(candidate: TopicCandidate) -> bool:
    if _title_relevance(candidate) > 0:
        return True
    return candidate.source.metadata.get("discovery_method") == "targeted_search"


def _candidate_score(candidate: TopicCandidate) -> float:
    metadata = candidate.source.metadata
    raw_points = metadata.get("points", 0)
    raw_comments = metadata.get("comment_count", 0)
    points = raw_points if isinstance(raw_points, int) else 0
    comments = raw_comments if isinstance(raw_comments, int) else 0
    targeted_bonus = (
        _TARGETED_SOURCE_BONUS
        if metadata.get("discovery_method") == "targeted_search"
        else 0.0
    )

    return (
        _title_relevance(candidate) * _RELEVANCE_WEIGHT
        + targeted_bonus
        + min(points, _MAX_POINTS_CONTRIBUTION) * _POINT_WEIGHT
        + min(comments, _MAX_COMMENTS_CONTRIBUTION) * _COMMENT_WEIGHT
    )
