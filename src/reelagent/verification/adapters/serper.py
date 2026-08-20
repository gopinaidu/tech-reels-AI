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
_MAX_TOKEN_OCCURRENCES = 5
_SEARCH_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "does",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "supports",
        "that",
        "the",
        "this",
        "to",
        "with",
    }
)


class SerperVerificationSearchError(RuntimeError):
    """Raised when Serper search fails unexpectedly."""


class SerperVerificationSearchClient:
    """Find trusted verification evidence through Serper and fetch official pages."""

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

        domains = domains_for_query(query)
        if not domains:
            return ()

        trusted_hosts = frozenset(host for domain in domains for host in domain.hosts)
        source_kinds = {
            host: domain.source_kind
            for domain in domains
            for host in domain.hosts
        }
        search_query = _build_search_query(query)
        headers = {
            "X-API-KEY": self._api_key.get_secret_value(),
            "Content-Type": "application/json",
        }
        payload = {"q": search_query, "num": min(max(limit * 2, 10), 20)}

        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            try:
                response = await client.post(
                    _SERPER_SEARCH_URL,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
            except httpx.HTTPStatusError as exc:
                detail = _response_error_detail(exc.response)
                raise SerperVerificationSearchError(
                    f"Serper search returned HTTP {exc.response.status_code}: {detail}"
                ) from exc
            except httpx.HTTPError as exc:
                raise SerperVerificationSearchError(
                    f"Serper search request failed: {type(exc).__name__}"
                ) from exc
            except ValueError as exc:
                raise SerperVerificationSearchError(
                    "Serper search returned invalid JSON"
                ) from exc

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
                if not isinstance(url, str) or not isinstance(title, str) or not title.strip():
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
                        title=title.strip()[:300],
                        url=HttpUrl(url),
                        snippet=snippet.strip()[:_MAX_EVIDENCE_SUMMARY_CHARS],
                        source_kind=source_kinds[host],
                    )
                )
                if len(hits) >= limit:
                    break

        return tuple(hits)


def _build_search_query(query: str) -> str:
    """Build a concise operator-free query compatible with Serper free accounts."""

    tokens = _tokens(query)
    meaningful = [token for token in tokens if token not in _SEARCH_STOP_WORDS]
    concise = meaningful[:10]
    if not concise:
        return query.strip()
    return f"{' '.join(concise)} documentation"


def _response_error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        message = body.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()[:300]
    text = response.text.strip()
    return text[:300] if text else response.reason_phrase


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
    if not tokens:
        return text[:_MAX_EVIDENCE_SUMMARY_CHARS]

    lowered = text.lower()
    candidates: list[tuple[int, int]] = []
    for token in tokens:
        search_from = 0
        for _ in range(_MAX_TOKEN_OCCURRENCES):
            position = lowered.find(token, search_from)
            if position < 0:
                break
            start = max(0, position - 500)
            end = min(len(text), start + _MAX_EVIDENCE_SUMMARY_CHARS)
            window = lowered[start:end]
            score = sum(1 for query_token in tokens if query_token in window)
            candidates.append((score, start))
            search_from = position + len(token)

    if not candidates:
        return text[:_MAX_EVIDENCE_SUMMARY_CHARS]

    _, best_start = max(candidates, key=lambda item: (item[0], item[1]))
    best_end = min(len(text), best_start + _MAX_EVIDENCE_SUMMARY_CHARS)
    best_start = max(0, best_end - _MAX_EVIDENCE_SUMMARY_CHARS)
    return text[best_start:best_end]
