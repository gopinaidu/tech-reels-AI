from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import HttpUrl

from reelagent.topics.models import DiscoveryQuery, SourceEvidence, SourceKind, TopicCandidate

_HN_SEARCH_BASE_URL = "https://hn.algolia.com/api/v1/"
_HN_DISCUSSION_URL = "https://news.ycombinator.com/item?id={item_id}"


class HackerNewsSearchError(RuntimeError):
    """Raised when targeted Hacker News search cannot return trustworthy results."""


class HackerNewsSearchSource:
    """Search Hacker News stories for one configured technical query."""

    def __init__(
        self,
        *,
        search_term: str,
        topic_group: str,
        min_points: int = 10,
        min_comments: int = 5,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.search_term = search_term
        self.topic_group = topic_group
        self.min_points = min_points
        self.min_comments = min_comments
        self._timeout = httpx.Timeout(timeout_seconds)
        self._transport = transport

    async def discover(self, query: DiscoveryQuery) -> list[TopicCandidate]:
        params: dict[str, str | int] = {
            "query": self.search_term,
            "tags": "story",
            "hitsPerPage": min(query.limit * 3, 100),
        }
        if query.since is not None:
            params["numericFilters"] = f"created_at_i>{int(query.since.timestamp())}"

        try:
            async with httpx.AsyncClient(
                base_url=_HN_SEARCH_BASE_URL,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.get("search_by_date", params=params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            raise HackerNewsSearchError("Hacker News targeted search failed") from exc

        hits = payload.get("hits") if isinstance(payload, dict) else None
        if not isinstance(hits, list):
            raise HackerNewsSearchError("Hacker News search response is missing hits")

        discovered_at = datetime.now(UTC)
        candidates: list[TopicCandidate] = []
        for hit in hits:
            candidate = self._to_candidate(hit, discovered_at=discovered_at)
            if candidate is not None:
                candidates.append(candidate)
            if len(candidates) >= query.limit:
                break
        return candidates

    def _to_candidate(
        self,
        hit: Any,
        *,
        discovered_at: datetime,
    ) -> TopicCandidate | None:
        if not isinstance(hit, dict):
            return None
        item_id = hit.get("objectID")
        title = hit.get("title")
        created_at_i = hit.get("created_at_i")
        if not isinstance(item_id, str) or not isinstance(title, str):
            return None
        if not isinstance(created_at_i, int):
            return None

        points = hit.get("points") if isinstance(hit.get("points"), int) else 0
        comments = hit.get("num_comments") if isinstance(hit.get("num_comments"), int) else 0
        if points < self.min_points and comments < self.min_comments:
            return None

        published_at = datetime.fromtimestamp(created_at_i, tz=UTC)
        source = SourceEvidence(
            source_name="Hacker News",
            source_kind=SourceKind.HACKER_NEWS,
            url=HttpUrl(_HN_DISCUSSION_URL.format(item_id=item_id)),
            external_id=item_id,
            published_at=published_at,
            metadata={
                "author": hit.get("author"),
                "points": points,
                "comment_count": comments,
                "article_url": hit.get("url"),
                "discovery_method": "targeted_search",
                "matched_topic_group": self.topic_group,
                "matched_query": self.search_term,
            },
        )
        return TopicCandidate(
            title=title,
            summary=f"Hacker News story matching {self.search_term}: {title}",
            discovered_at=discovered_at,
            source=source,
        )
