from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import quote_plus, urljoin, urlparse
from xml.etree import ElementTree

import httpx
from pydantic import HttpUrl

from reelagent.topics.models import SourceKind
from reelagent.verification.adapters.search import VerificationSearchHit

_TAG_RE = re.compile(r"<[^>]+>")
_HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)
_WS_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9_.+-]*")
_MAX_EVIDENCE_SUMMARY_CHARS = 2_000
_MAX_PAGE_TEXT_CHARS = 100_000
_MAX_SITE_SEARCH_CANDIDATES = 50
_DOC_PATH_MARKERS = ("/docs/", "/documentation/", "/reference/", "/manual/", "/guide/")
_LOW_VALUE_PATH_MARKERS = ("/about/news/", "/news/", "/blog/", "/events/")


@dataclass(frozen=True)
class AuthoritativeDomain:
    name: str
    hosts: tuple[str, ...]
    keywords: tuple[str, ...]
    sitemap_urls: tuple[str, ...]
    source_kind: SourceKind = SourceKind.OFFICIAL
    search_url_template: str | None = None


_DEFAULT_DOMAINS: tuple[AuthoritativeDomain, ...] = (
    AuthoritativeDomain(
        name="PostgreSQL",
        hosts=("postgresql.org", "www.postgresql.org"),
        keywords=("postgres", "postgresql", "sql", "jsonb", "skip locked"),
        sitemap_urls=("https://www.postgresql.org/sitemap.xml",),
        search_url_template="https://www.postgresql.org/search/?q={query}",
    ),
    AuthoritativeDomain(
        name="Apache Kafka",
        hosts=("kafka.apache.org",),
        keywords=("kafka", "consumer", "producer", "topic", "partition"),
        sitemap_urls=("https://kafka.apache.org/sitemap.xml",),
    ),
    AuthoritativeDomain(
        name="Kubernetes",
        hosts=("kubernetes.io",),
        keywords=("kubernetes", "k8s", "pod", "deployment", "container"),
        sitemap_urls=("https://kubernetes.io/sitemap.xml",),
    ),
    AuthoritativeDomain(
        name="Python",
        hosts=("docs.python.org", "python.org", "www.python.org"),
        keywords=("python", "cpython", "asyncio", "gil"),
        sitemap_urls=("https://docs.python.org/3/sitemap.xml",),
    ),
    AuthoritativeDomain(
        name="AWS",
        hosts=("docs.aws.amazon.com", "aws.amazon.com"),
        keywords=("aws", "amazon web services", "lambda", "dynamodb", "s3", "ec2"),
        sitemap_urls=("https://docs.aws.amazon.com/sitemap_index.xml",),
    ),
    AuthoritativeDomain(
        name="Google Cloud",
        hosts=("cloud.google.com",),
        keywords=("gcp", "google cloud", "gke", "bigquery", "cloud run"),
        sitemap_urls=("https://cloud.google.com/sitemap.xml",),
    ),
    AuthoritativeDomain(
        name="OpenJDK",
        hosts=("openjdk.org", "docs.oracle.com"),
        keywords=("java", "jdk", "jvm", "openjdk", "virtual threads"),
        sitemap_urls=("https://openjdk.org/sitemap.xml",),
    ),
    AuthoritativeDomain(
        name="GitHub",
        hosts=("github.com", "docs.github.com"),
        keywords=("github", "git", "actions", "pull request"),
        sitemap_urls=("https://docs.github.com/sitemap.xml",),
        source_kind=SourceKind.GITHUB,
    ),
)


class AuthoritativeDomainSearchError(RuntimeError):
    """Raised when curated authoritative-domain retrieval fails unexpectedly."""


class AuthoritativeDomainSearchClient:
    """Search curated official documentation without a general web-search provider."""

    def __init__(
        self,
        *,
        domains: tuple[AuthoritativeDomain, ...] = _DEFAULT_DOMAINS,
        timeout_seconds: float = 10.0,
        max_sitemap_urls: int = 5_000,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._domains = domains
        self._timeout = httpx.Timeout(timeout_seconds)
        self._max_sitemap_urls = max_sitemap_urls
        self._transport = transport

    async def search(self, query: str, *, limit: int) -> tuple[VerificationSearchHit, ...]:
        if limit < 1 or limit > 10:
            raise ValueError("limit must be between 1 and 10")
        selected = _select_domains(query, self._domains)
        if not selected:
            return ()

        tokens = _tokens(query)
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            site_hits: list[tuple[int, VerificationSearchHit]] = []
            for domain in selected:
                search_urls = await _read_site_search(client, domain, query)
                for url in search_urls:
                    page_text = await _fetch_page_text(client, url)
                    if not page_text:
                        continue
                    score = _content_score(page_text, tokens) + _url_score(url, tokens)
                    if score <= 0:
                        continue
                    site_hits.append(
                        (
                            score,
                            VerificationSearchHit(
                                title=_title_from_url(url),
                                url=HttpUrl(url),
                                snippet=_relevant_excerpt(page_text, tokens),
                                source_kind=domain.source_kind,
                            ),
                        )
                    )

            if site_hits:
                site_hits.sort(key=lambda item: (-item[0], str(item[1].url)))
                return tuple(hit for _, hit in site_hits[:limit])

            candidates: list[tuple[int, AuthoritativeDomain, str]] = []
            for domain in selected:
                try:
                    urls = await self._load_domain_urls(client, domain)
                except AuthoritativeDomainSearchError:
                    continue
                for url in urls:
                    score = _url_score(url, tokens)
                    if score > 0:
                        candidates.append((score, domain, url))

            candidates.sort(key=lambda item: (-item[0], item[2]))
            hits: list[VerificationSearchHit] = []
            seen: set[str] = set()
            for _, domain, url in candidates:
                if url in seen:
                    continue
                seen.add(url)
                page_text = await _fetch_page_text(client, url)
                if not page_text:
                    continue
                hits.append(
                    VerificationSearchHit(
                        title=_title_from_url(url),
                        url=HttpUrl(url),
                        snippet=_relevant_excerpt(page_text, tokens),
                        source_kind=domain.source_kind,
                    )
                )
                if len(hits) >= limit:
                    break
        return tuple(hits)

    async def _load_domain_urls(
        self,
        client: httpx.AsyncClient,
        domain: AuthoritativeDomain,
    ) -> tuple[str, ...]:
        urls: list[str] = []
        for sitemap_url in domain.sitemap_urls:
            found = await _read_sitemap(
                client,
                sitemap_url,
                domain.hosts,
                self._max_sitemap_urls,
            )
            urls.extend(found)
            if len(urls) >= self._max_sitemap_urls:
                break
        return tuple(urls[: self._max_sitemap_urls])


def _select_domains(
    query: str,
    domains: Iterable[AuthoritativeDomain],
) -> tuple[AuthoritativeDomain, ...]:
    lowered = query.lower()
    return tuple(
        domain
        for domain in domains
        if any(keyword in lowered for keyword in domain.keywords)
    )


def _tokens(text: str) -> frozenset[str]:
    return frozenset(token for token in _WORD_RE.findall(text.lower()) if len(token) >= 3)


def _url_score(url: str, tokens: frozenset[str]) -> int:
    parsed = urlparse(url)
    path = parsed.path.lower().replace("-", " ").replace("_", " ").replace("/", " ")
    score = sum(2 for token in tokens if token in path)
    raw_path = parsed.path.lower()
    if any(marker in raw_path for marker in _DOC_PATH_MARKERS):
        score += 8
    if any(marker in raw_path for marker in _LOW_VALUE_PATH_MARKERS):
        score -= 8
    return score


def _content_score(text: str, tokens: frozenset[str]) -> int:
    lowered = text.lower()
    score = sum(5 for token in tokens if token in lowered)
    if "skip locked" in lowered:
        score += 25
    if "queue-like" in lowered or "queue like" in lowered:
        score += 15
    if "multiple consumers" in lowered:
        score += 10
    return score


def _relevant_excerpt(text: str, tokens: frozenset[str]) -> str:
    if len(text) <= _MAX_EVIDENCE_SUMMARY_CHARS:
        return text

    lowered = text.lower()
    anchors = ["skip locked", "queue-like", "queue like", "multiple consumers"]
    positions = [lowered.find(anchor) for anchor in anchors if lowered.find(anchor) >= 0]
    positions.extend(lowered.find(token) for token in tokens if lowered.find(token) >= 0)
    if not positions:
        return text[:_MAX_EVIDENCE_SUMMARY_CHARS]

    center = min(positions)
    start = max(0, center - 500)
    end = min(len(text), start + _MAX_EVIDENCE_SUMMARY_CHARS)
    start = max(0, end - _MAX_EVIDENCE_SUMMARY_CHARS)
    return text[start:end]


async def _read_site_search(
    client: httpx.AsyncClient,
    domain: AuthoritativeDomain,
    query: str,
) -> tuple[str, ...]:
    if domain.search_url_template is None:
        return ()
    search_url = domain.search_url_template.format(query=quote_plus(query))
    try:
        response = await client.get(search_url, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError:
        return ()

    urls: list[str] = []
    seen: set[str] = set()
    for href in _HREF_RE.findall(response.text):
        url = urljoin(search_url, html.unescape(href))
        if url in seen or not _allowed_url(url, domain.hosts):
            continue
        if not any(marker in urlparse(url).path.lower() for marker in _DOC_PATH_MARKERS):
            continue
        seen.add(url)
        urls.append(url)
        if len(urls) >= _MAX_SITE_SEARCH_CANDIDATES:
            break
    return tuple(urls)


async def _read_sitemap(
    client: httpx.AsyncClient,
    sitemap_url: str,
    allowed_hosts: tuple[str, ...],
    limit: int,
) -> list[str]:
    if limit <= 0:
        return []
    try:
        response = await client.get(sitemap_url)
        response.raise_for_status()
        root = ElementTree.fromstring(response.text)
    except (httpx.HTTPError, ElementTree.ParseError) as exc:
        raise AuthoritativeDomainSearchError(
            f"Failed to read sitemap: {sitemap_url}"
        ) from exc

    locations = [
        element.text.strip()
        for element in root.iter()
        if element.tag.endswith("loc") and element.text
    ]
    if root.tag.endswith("sitemapindex"):
        urls: list[str] = []
        for child in locations[:10]:
            urls.extend(await _read_sitemap(client, child, allowed_hosts, limit - len(urls)))
            if len(urls) >= limit:
                break
        return urls[:limit]

    return [url for url in locations if _allowed_url(url, allowed_hosts)][:limit]


def _allowed_url(url: str, allowed_hosts: tuple[str, ...]) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and (parsed.hostname or "").lower() in allowed_hosts


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


def _title_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    tail = path.rsplit("/", 1)[-1] if path else parsed.hostname or "Documentation"
    title = tail.replace("-", " ").replace("_", " ").strip()
    return title[:300] or "Documentation"
