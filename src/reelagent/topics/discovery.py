from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from reelagent.config import Settings
from reelagent.topics.adapters.hacker_news import HackerNewsDiscoverySource
from reelagent.topics.adapters.hacker_news_search import HackerNewsSearchSource
from reelagent.topics.models import DiscoveryQuery, TopicCandidate
from reelagent.topics.persistence import build_dedupe_key


class HackerNewsDiscoveryCoordinator:
    """Combine broad HN trending discovery with configured targeted searches."""

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

        trending_by_key = {build_dedupe_key(candidate): candidate for candidate in trending}
        targeted_by_key: dict[str, TopicCandidate] = {}
        for candidates in targeted_sets:
            for candidate in candidates:
                key = build_dedupe_key(candidate)
                if key in trending_by_key:
                    continue
                existing = targeted_by_key.get(key)
                if existing is None or _candidate_signal(candidate) > _candidate_signal(existing):
                    targeted_by_key[key] = candidate

        targeted = sorted(targeted_by_key.values(), key=_candidate_signal, reverse=True)
        return trending + targeted[: self.settings.hn_targeted_total_limit]


def _candidate_signal(candidate: TopicCandidate) -> tuple[int, int]:
    metadata = candidate.source.metadata
    points = metadata.get("points", 0)
    comments = metadata.get("comment_count", 0)
    return (
        points if isinstance(points, int) else 0,
        comments if isinstance(comments, int) else 0,
    )
