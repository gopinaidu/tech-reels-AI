from __future__ import annotations

import html
import re
from urllib.parse import urlparse

import httpx
from pydantic import HttpUrl, SecretStr

from reelagent.verification.adapters.search import VerificationSearchHit
from reelagent.verification.trust import domains_for_query, is_trusted_url

_SERPER_SEARCH_URL = "https://google.serper.dev/search"
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9_.+-]*")
_MAX_PAGE_TEXT_CHARS = 100_000
_MAX_EVIDENCE_SUMMARY_CHARS = 2_000


class SerperVerificationSearchError(RuntimeError):
    """Raised when Serper search fails unexpectedly."""


class SerperVerificationSearchClient:
    """Find trusted verification evidence through Serper and fetch official pages."""

    def __init__(
        self,
        *,
        api_key: SecretStr,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._timeout = httpx.Timeout(timeout_seconds)
        self._transport = transport

    async def search(self, query: str, *, limit: int) -> tuple[VerificationSearchHit, ...]:
        if limit < 1 or limit > 10:
            raise ValueError("limit must be between 1 and 10")

        domains = domains_for_query(query)
        if not domains:
            return ()

        trusted_hosts = frozenset(host for domain in domains for host in domain.hosts)
        source_kinds = {
            host: domain.source_kind
            for domain in domains
            for host in domain.hosts
        }
        search_query = _build_search_query(query, trusted_hosts)
        headers = {
            "X-API-KEY": self._api_key.get_secret_value(),
            "Content-Type": "application/json",
        }
        payload = {"q": search_query, "num": min(max(limit * 3, 10), 30)}

        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            try:
                response = await client.post(
                    _SERPER_SEARCH_URL,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise SerperVerificationSearchError("Serper search request failed") from exc

            results = body.get("organic", [])
            if not isinstance(results, list):
                return ()

            hits: list[VerificationSearchHit] = []
            seen: set[str] = set()
            tokens = _tokens(query)
            for item in results:
                if not isinstance(item, dict):
                    continue
                url = item.get("link")
                title = item.get("title")
                if not isinstance(url, str) or not isinstance(title, str):
                    continue
                if url in seen or not is_trusted_url(url, trusted_hosts):
                    continue
                seen.add(url)

                page_text = await _fetch_page_text(client, url)
                snippet = _relevant_excerpt(page_text, tokens) if page_text else item.get("snippet")
                if not isinstance(snippet, str) or not snippet.strip():
                    continue

                host = (urlparse(url).hostname or "").lower()
                hits.append(
                    VerificationSearchHit(
                        title=title[:300],
                        url=HttpUrl(url),
                        snippet=snippet[:_MAX_EVIDENCE_SUMMARY_CHARS],
                        source_kind=source_kinds[host],
                    )
                )
                if len(hits) >= limit:
                    break

        return tuple(hits)


def _build_search_query(query: str, hosts: frozenset[str]) -> str:
    site_terms = " OR ".join(f"site:{host}" for host in sorted(hosts))
    return f"{query} ({site_terms})"


def _tokens(text: str) -> tuple[str, ...]:
    seen: set[str] = set()
    tokens: list[str] = []
    for token in _WORD_RE.findall(text.lower()):
        if len(token) < 3 or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tuple(tokens)


async def _fetch_page_text(client: httpx.AsyncClient, url: str) -> str:
    try:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError:
        return ""
    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "text/plain" not in content_type:
        return ""
    text = html.unescape(_TAG_RE.sub(" ", response.text))
    normalized = _WS_RE.sub(" ", text).strip()
    return normalized[:_MAX_PAGE_TEXT_CHARS]


def _relevant_excerpt(text: str, tokens: tuple[str, ...]) -> str:
    if len(text) <= _MAX_EVIDENCE_SUMMARY_CHARS:
        return text

    lowered = text.lower()
    positions = [lowered.find(token) for token in tokens if lowered.find(token) >= 0]
    if not positions:
        return text[:_MAX_EVIDENCE_SUMMARY_CHARS]

    center = min(positions)
    start = max(0, center - 400)
    end = min(len(text), start + _MAX_EVIDENCE_SUMMARY_CHARS)
    start = max(0, end - _MAX_EVIDENCE_SUMMARY_CHARS)
    return text[start:end]
