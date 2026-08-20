from __future__ import annotations

import html
import re
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import HttpUrl

from reelagent.config import Settings
from reelagent.intelligence.models import Evidence, EvidenceRole, TopicEvidencePackage
from reelagent.topics.models import SourceEvidence, SourceKind, TopicCandidate

_HN_ITEM_API_BASE_URL = "https://hn.algolia.com/api/v1/"
_HN_DISCUSSION_URL = "https://news.ycombinator.com/item?id={item_id}"
_MAX_EVIDENCE_TEXT = 2_000

_INSTRUCTION_PATTERNS = (
    re.compile(r"\bignore (?:all |any )?(?:previous|prior) instructions\b", re.IGNORECASE),
    re.compile(r"\bsystem prompt\b", re.IGNORECASE),
    re.compile(r"\bfollow (?:these|the following) instructions\b", re.IGNORECASE),
    re.compile(r"\byou are chatgpt\b", re.IGNORECASE),
)


class HackerNewsEvidenceCollectionError(RuntimeError):
    """Raised when Hacker News evidence cannot be collected safely."""


class HackerNewsEvidenceCollector:
    """Collect bounded HN story metadata and ranked discussion evidence."""

    def __init__(
        self,
        settings: Settings,
        *,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self._timeout = httpx.Timeout(timeout_seconds)
        self._transport = transport

    async def collect(self, topic: TopicCandidate) -> TopicEvidencePackage:
        if topic.source.source_kind != SourceKind.HACKER_NEWS:
            raise ValueError("HackerNewsEvidenceCollector requires a Hacker News topic")
        if topic.source.external_id is None:
            raise ValueError("Hacker News topic is missing external_id")

        payload = await self._fetch_item(topic.source.external_id)
        retrieved_at = datetime.now(UTC)
        evidence: list[Evidence] = [self._story_evidence(topic, payload, retrieved_at)]

        comments = _flatten_comments(
            payload.get("children"),
            scan_limit=self.settings.hn_evidence_comment_scan_limit,
        )
        ranked = sorted(comments, key=_comment_score, reverse=True)
        for comment in ranked[: self.settings.hn_evidence_comment_limit]:
            evidence.append(self._comment_evidence(comment, retrieved_at))

        return TopicEvidencePackage(topic=topic, evidence=tuple(evidence))

    async def _fetch_item(self, external_id: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                base_url=_HN_ITEM_API_BASE_URL,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.get(f"items/{external_id}")
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            raise HackerNewsEvidenceCollectionError(
                "Hacker News evidence collection failed"
            ) from exc

        if not isinstance(payload, dict):
            raise HackerNewsEvidenceCollectionError("Hacker News item response must be an object")
        return payload

    def _story_evidence(
        self,
        topic: TopicCandidate,
        payload: dict[str, Any],
        retrieved_at: datetime,
    ) -> Evidence:
        item_id = str(payload.get("id") or topic.source.external_id)
        title = payload.get("title") if isinstance(payload.get("title"), str) else topic.title
        points = payload.get("points") if isinstance(payload.get("points"), int) else 0
        children = payload.get("children")
        comment_count = len(children) if isinstance(children, list) else 0
        published_at = _timestamp(payload.get("created_at_i")) or topic.source.published_at
        article_url = payload.get("url") if isinstance(payload.get("url"), str) else None
        summary = _truncate(
            f"Hacker News story: {title}. Points: {points}. "
            f"Top-level comments: {comment_count}."
        )
        source = SourceEvidence(
            source_name="Hacker News",
            source_kind=SourceKind.HACKER_NEWS,
            url=HttpUrl(_HN_DISCUSSION_URL.format(item_id=item_id)),
            external_id=item_id,
            published_at=published_at,
            metadata={
                "author": payload.get("author"),
                "points": points,
                "top_level_comment_count": comment_count,
                "article_url": article_url,
                "evidence_type": "story_metadata",
            },
        )
        return Evidence(
            evidence_id=f"hn-story:{item_id}",
            source=source,
            roles=frozenset({EvidenceRole.DISCOVERY, EvidenceRole.DISCUSSION}),
            summary=summary,
            retrieved_at=retrieved_at,
        )

    def _comment_evidence(self, comment: _RankedComment, retrieved_at: datetime) -> Evidence:
        source = SourceEvidence(
            source_name="Hacker News Comment",
            source_kind=SourceKind.HACKER_NEWS,
            url=HttpUrl(_HN_DISCUSSION_URL.format(item_id=comment.comment_id)),
            external_id=str(comment.comment_id),
            published_at=comment.published_at,
            metadata={
                "author": comment.author,
                "parent_id": comment.parent_id,
                "depth": comment.depth,
                "reply_count": comment.reply_count,
                "selection_score": _comment_score(comment),
                "evidence_type": "discussion_comment",
            },
        )
        return Evidence(
            evidence_id=f"hn-comment:{comment.comment_id}",
            source=source,
            roles=frozenset({EvidenceRole.DISCUSSION}),
            summary=_truncate(comment.text),
            retrieved_at=retrieved_at,
            instruction_like_content_detected=_contains_instruction_like_content(comment.text),
        )


class _RankedComment:
    def __init__(
        self,
        *,
        comment_id: int,
        parent_id: int | None,
        author: str,
        text: str,
        depth: int,
        reply_count: int,
        published_at: datetime | None,
    ) -> None:
        self.comment_id = comment_id
        self.parent_id = parent_id
        self.author = author
        self.text = text
        self.depth = depth
        self.reply_count = reply_count
        self.published_at = published_at


def _flatten_comments(children: Any, *, scan_limit: int) -> list[_RankedComment]:
    if not isinstance(children, list):
        return []

    flattened: list[_RankedComment] = []
    stack: list[tuple[Any, int, int | None]] = [
        (child, 0, None) for child in reversed(children)
    ]
    while stack and len(flattened) < scan_limit:
        raw, depth, parent_id = stack.pop()
        if not isinstance(raw, dict):
            continue

        comment_id = raw.get("id")
        author = raw.get("author")
        text = _clean_comment_text(raw.get("text"))
        raw_children = raw.get("children")
        child_list = raw_children if isinstance(raw_children, list) else []

        if isinstance(comment_id, int) and isinstance(author, str) and text:
            flattened.append(
                _RankedComment(
                    comment_id=comment_id,
                    parent_id=parent_id,
                    author=author,
                    text=text,
                    depth=depth,
                    reply_count=len(child_list),
                    published_at=_timestamp(raw.get("created_at_i")),
                )
            )
            next_parent_id: int | None = comment_id
        else:
            next_parent_id = parent_id

        for child in reversed(child_list):
            stack.append((child, depth + 1, next_parent_id))

    return flattened


def _comment_score(comment: _RankedComment) -> float:
    substantive_length = min(len(comment.text), 1_200) / 200
    reply_signal = min(comment.reply_count, 20) * 4
    top_level_bonus = max(0, 3 - comment.depth)
    return reply_signal + substantive_length + top_level_bonus


def _clean_comment_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = re.sub(r"(?i)<\s*(?:p|br)\s*/?>", "\n", value)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _contains_instruction_like_content(text: str) -> bool:
    return any(pattern.search(text) is not None for pattern in _INSTRUCTION_PATTERNS)


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, int):
        return None
    return datetime.fromtimestamp(value, tz=UTC)


def _truncate(text: str) -> str:
    return text[:_MAX_EVIDENCE_TEXT]
