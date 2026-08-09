import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from reelagent.topics.adapters.hacker_news import (
    HackerNewsDiscoveryError,
    HackerNewsDiscoverySource,
)
from reelagent.topics.models import DiscoveryQuery, SourceKind


def test_discover_maps_hacker_news_story_to_topic_candidate() -> None:
    published_at = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/topstories.json"):
            return httpx.Response(200, json=[101])
        if request.url.path.endswith("/item/101.json"):
            return httpx.Response(
                200,
                json={
                    "id": 101,
                    "type": "story",
                    "by": "engineer",
                    "time": int(published_at.timestamp()),
                    "title": "A useful distributed systems release",
                    "url": "https://example.com/release",
                    "score": 120,
                },
            )
        raise AssertionError(f"Unexpected request: {request.url}")

    source = HackerNewsDiscoverySource(transport=httpx.MockTransport(handler))
    candidates = asyncio.run(source.discover(DiscoveryQuery(limit=1)))

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.title == "A useful distributed systems release"
    assert candidate.source.source_kind == SourceKind.HACKER_NEWS
    assert candidate.source.external_id == "101"
    assert candidate.source.published_at == published_at
    assert str(candidate.source.url) == "https://news.ycombinator.com/item?id=101"


def test_discover_filters_old_dead_and_non_story_items() -> None:
    cutoff = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)

    items = {
        1: {
            "id": 1,
            "type": "story",
            "time": int(datetime(2026, 8, 8, 11, 0, tzinfo=UTC).timestamp()),
            "title": "Too old",
        },
        2: {
            "id": 2,
            "type": "story",
            "time": int(datetime(2026, 8, 8, 13, 0, tzinfo=UTC).timestamp()),
            "title": "Dead story",
            "dead": True,
        },
        3: {
            "id": 3,
            "type": "job",
            "time": int(datetime(2026, 8, 8, 13, 0, tzinfo=UTC).timestamp()),
            "title": "Not a story",
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/topstories.json"):
            return httpx.Response(200, json=[1, 2, 3])
        item_id = int(request.url.path.split("/")[-1].removesuffix(".json"))
        return httpx.Response(200, json=items[item_id])

    source = HackerNewsDiscoverySource(transport=httpx.MockTransport(handler))
    candidates = asyncio.run(source.discover(DiscoveryQuery(limit=3, since=cutoff)))

    assert candidates == []


def test_discover_wraps_http_failures() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    source = HackerNewsDiscoverySource(transport=httpx.MockTransport(handler))

    with pytest.raises(HackerNewsDiscoveryError, match="Hacker News discovery failed"):
        asyncio.run(source.discover(DiscoveryQuery(limit=1)))
