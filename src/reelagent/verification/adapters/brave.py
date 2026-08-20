from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import HttpUrl, SecretStr

from reelagent.topics.models import SourceKind
from reelagent.verification.adapters.search import VerificationSearchHit

_BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


class BraveVerificationSearchError(RuntimeError):
    """Raised when Brave Search cannot return usable verification results."""


class BraveVerificationSearchClient:
    """Use Brave Web Search as the concrete runtime verification search provider."""

    def __init__(
        self,
        *,
        api_key: SecretStr,
        timeout_seconds: float = 15.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._timeout = httpx.Timeout(timeout_seconds)
        self._transport = transport

    async def search(self, query: str, *, limit: int) -> tuple[VerificationSearchHit, ...]:
        if limit < 1 or limit > 10:
            raise ValueError("limit must be between 1 and 10")
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self._api_key.get_secret_value(),
        }
        params = {
            "q": query,
            "count": limit,
            "country": "US",
            "search_lang": "en",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.get(_BRAVE_SEARCH_URL, headers=headers, params=params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            raise BraveVerificationSearchError("Brave verification search failed") from exc

        return _parse_web_results(payload, limit=limit)


def _parse_web_results(payload: Any, *, limit: int) -> tuple[VerificationSearchHit, ...]:
    if not isinstance(payload, dict):
        raise BraveVerificationSearchError("Brave response must be a JSON object")
    web = payload.get("web")
    if web is None:
        return ()
    if not isinstance(web, dict) or not isinstance(web.get("results"), list):
        raise BraveVerificationSearchError("Brave response has invalid web results")

    hits: list[VerificationSearchHit] = []
    for raw in web["results"][:limit]:
        if not isinstance(raw, dict):
            continue
        title = raw.get("title")
        url = raw.get("url")
        description = raw.get("description")
        if not all(isinstance(value, str) and value.strip() for value in (title, url, description)):
            continue
        published_at = _parse_age(raw.get("age"))
        hits.append(
            VerificationSearchHit(
                title=title.strip(),
                url=HttpUrl(url),
                snippet=description.strip(),
                source_kind=_classify_source(url),
                published_at=published_at,
            )
        )
    return tuple(hits)


def _classify_source(url: str) -> SourceKind:
    host = (urlparse(url).hostname or "").lower()
    if host == "github.com" or host.endswith(".github.com"):
        return SourceKind.GITHUB
    if host in {"arxiv.org", "doi.org"} or host.endswith(".acm.org") or host.endswith(".ieee.org"):
        return SourceKind.RESEARCH
    if _looks_like_official_docs(host):
        return SourceKind.OFFICIAL
    return SourceKind.ENGINEERING_BLOG


def _looks_like_official_docs(host: str) -> bool:
    markers = ("docs.", "developer.", "developers.", "documentation.", "api.")
    return host.startswith(markers) or host in {
        "postgresql.org",
        "www.postgresql.org",
        "kubernetes.io",
        "docs.python.org",
        "docs.oracle.com",
    }


def _parse_age(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None
