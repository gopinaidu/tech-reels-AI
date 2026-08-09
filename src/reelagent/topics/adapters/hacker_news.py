import asyncio
from datetime import UTC, datetime
from typing import TypedDict, cast

import httpx
from pydantic import HttpUrl

from reelagent.topics.models import DiscoveryQuery, SourceEvidence, SourceKind, TopicCandidate

_HN_API_BASE_URL = "https://hacker-news.firebaseio.com/v0/"
_HN_DISCUSSION_URL = "https://news.ycombinator.com/item?id={item_id}"
_MAX_SCAN_ITEMS = 100


class HackerNewsDiscoveryError(RuntimeError):
    """Raised when Hacker News discovery cannot return a trustworthy result."""


class _HackerNewsItem(TypedDict, total=False):
    id: int
    deleted: bool
    type: str
    by: str
    time: int
    dead: bool
    title: str
    url: str
    score: int
    descendants: int


class HackerNewsDiscoverySource:
    """Discover topic candidates from Hacker News top stories."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._timeout = httpx.Timeout(timeout_seconds)
        self._transport = transport

    async def discover(self, query: DiscoveryQuery) -> list[TopicCandidate]:
        discovered_at = datetime.now(UTC)

        try:
            async with httpx.AsyncClient(
                base_url=_HN_API_BASE_URL,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                story_ids = await self._fetch_top_story_ids(client)
                scan_count = min(max(query.limit * 3, query.limit), _MAX_SCAN_ITEMS)
                items = await asyncio.gather(
                    *(self._fetch_item(client, item_id) for item_id in story_ids[:scan_count])
                )
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            raise HackerNewsDiscoveryError("Hacker News discovery failed") from exc

        candidates: list[TopicCandidate] = []
        for rank, item in enumerate(items, start=1):
            candidate = self._to_candidate(
                item,
                discovered_at=discovered_at,
                query=query,
                rank=rank,
            )
            if candidate is not None:
                candidates.append(candidate)
            if len(candidates) >= query.limit:
                break

        return candidates

    async def _fetch_top_story_ids(self, client: httpx.AsyncClient) -> list[int]:
        response = await client.get("topstories.json")
        response.raise_for_status()
        payload = response.json()
        valid_payload = isinstance(payload, list) and all(
            isinstance(item_id, int) for item_id in payload
        )
        if not valid_payload:
            raise ValueError("topstories response must be a list of integer ids")
        return cast(list[int], payload)

    async def _fetch_item(self, client: httpx.AsyncClient, item_id: int) -> _HackerNewsItem:
        response = await client.get(f"item/{item_id}.json")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("item response must be an object")
        return cast(_HackerNewsItem, payload)

    def _to_candidate(
        self,
        item: _HackerNewsItem,
        *,
        discovered_at: datetime,
        query: DiscoveryQuery,
        rank: int,
    ) -> TopicCandidate | None:
        if item.get("deleted") or item.get("dead") or item.get("type") != "story":
            return None

        item_id = item.get("id")
        title = item.get("title")
        timestamp = item.get("time")
        if (
            not isinstance(item_id, int)
            or not isinstance(title, str)
            or not isinstance(timestamp, int)
        ):
            return None

        published_at = datetime.fromtimestamp(timestamp, tz=UTC)
        if query.since is not None and published_at < query.since:
            return None

        source = SourceEvidence(
            source_name="Hacker News",
            source_kind=SourceKind.HACKER_NEWS,
            url=HttpUrl(_HN_DISCUSSION_URL.format(item_id=item_id)),
            external_id=str(item_id),
            published_at=published_at,
            metadata={
                "author": item.get("by"),
                "points": item.get("score", 0),
                "comment_count": item.get("descendants", 0),
                "article_url": item.get("url"),
                "hn_rank": rank,
                "discovery_method": "trending",
            },
        )
        return TopicCandidate(
            title=title,
            summary=f"Hacker News story: {title}",
            discovered_at=discovered_at,
            source=source,
        )
