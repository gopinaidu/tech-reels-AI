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
        tasks = []
        if self.settings.hn_trending_limit:
            tasks.append(
                self.trending_source.discover(
                    DiscoveryQuery(limit=self.settings.hn_trending_limit, since=since)
                )
            )

        for group, terms in self.settings.discovery_topic_groups.items():
            for term in terms:
                source = HackerNewsSearchSource(
                    search_term=term,
                    topic_group=group,
                    min_points=self.settings.hn_targeted_min_points,
                    min_comments=self.settings.hn_targeted_min_comments,
                )
                tasks.append(
                    source.discover(
                        DiscoveryQuery(
                            limit=self.settings.hn_targeted_limit_per_query,
                            since=since,
                        )
                    )
                )

        result_sets = await asyncio.gather(*tasks)
        unique: dict[str, TopicCandidate] = {}
        for candidates in result_sets:
            for candidate in candidates:
                key = build_dedupe_key(candidate)
                existing = unique.get(key)
                if existing is None:
                    unique[key] = candidate
                    continue
                if _candidate_signal(candidate) > _candidate_signal(existing):
                    unique[key] = candidate
        return list(unique.values())


def _candidate_signal(candidate: TopicCandidate) -> tuple[int, int]:
    metadata = candidate.source.metadata
    points = metadata.get("points", 0)
    comments = metadata.get("comment_count", 0)
    return (
        points if isinstance(points, int) else 0,
        comments if isinstance(comments, int) else 0,
    )
