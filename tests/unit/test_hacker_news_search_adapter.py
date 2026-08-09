import asyncio
from datetime import UTC, datetime

import httpx

from reelagent.topics.adapters.hacker_news_search import HackerNewsSearchSource
from reelagent.topics.models import DiscoveryQuery


def test_targeted_search_filters_low_signal_and_preserves_metadata() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/search_by_date")
        assert request.url.params["query"] == "Kafka"
        assert request.url.params["tags"] == "story"
        return httpx.Response(
            200,
            json={
                "hits": [
                    {
                        "objectID": "100",
                        "title": "Kafka gets a new queue primitive",
                        "created_at_i": 1786233600,
                        "author": "engineer",
                        "points": 42,
                        "num_comments": 18,
                        "url": "https://example.com/kafka",
                    },
                    {
                        "objectID": "101",
                        "title": "Low signal Kafka mention",
                        "created_at_i": 1786233600,
                        "points": 1,
                        "num_comments": 0,
                    },
                ]
            },
        )

    source = HackerNewsSearchSource(
        search_term="Kafka",
        topic_group="streaming",
        min_points=10,
        min_comments=5,
        transport=httpx.MockTransport(handler),
    )
    query = DiscoveryQuery(
        limit=5,
        since=datetime(2026, 8, 1, tzinfo=UTC),
    )
    candidates = asyncio.run(source.discover(query))

    assert len(candidates) == 1
    metadata = candidates[0].source.metadata
    assert metadata["points"] == 42
    assert metadata["comment_count"] == 18
    assert metadata["matched_topic_group"] == "streaming"
    assert metadata["matched_query"] == "Kafka"
    assert metadata["discovery_method"] == "targeted_search"
