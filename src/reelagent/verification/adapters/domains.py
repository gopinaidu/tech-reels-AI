from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx
from pydantic import HttpUrl

from reelagent.topics.models import SourceKind
from reelagent.verification.adapters.search import VerificationSearchHit

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9_.+-]*")


@dataclass(frozen=True)
class AuthoritativeDomain:
    name: str
    hosts: tuple[str, ...]
    keywords: tuple[str, ...]
    sitemap_urls: tuple[str, ...]
    source_kind: SourceKind = SourceKind.OFFICIAL


_DEFAULT_DOMAINS: tuple[AuthoritativeDomain, ...] = (
    AuthoritativeDomain(
        name="PostgreSQL",
        hosts=("postgresql.org", "www.postgresql.org"),
        keywords=("postgres", "postgresql", "sql", "jsonb", "skip locked"),
        sitemap_urls=("https://www.postgresql.org/sitemap.xml",),
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
        max_sitemap_urls: int = 500,
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
        candidates: list[tuple[int, AuthoritativeDomain, str]] = []
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
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
                snippet = await _fetch_snippet(client, url)
                if not snippet:
                    continue
                hits.append(
                    VerificationSearchHit(
                        title=_title_from_url(url),
                        url=HttpUrl(url),
                        snippet=snippet,
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
    lowered = url.lower().replace("-", " ").replace("_", " ").replace("/", " ")
    return sum(1 for token in tokens if token in lowered)


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
        for child in locations[:5]:
            urls.extend(await _read_sitemap(client, child, allowed_hosts, limit - len(urls)))
            if len(urls) >= limit:
                break
        return urls[:limit]

    return [url for url in locations if _allowed_url(url, allowed_hosts)][:limit]


def _allowed_url(url: str, allowed_hosts: tuple[str, ...]) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and (parsed.hostname or "").lower() in allowed_hosts


async def _fetch_snippet(client: httpx.AsyncClient, url: str) -> str:
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
    return normalized[:4_000]


def _title_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    tail = path.rsplit("/", 1)[-1] if path else parsed.hostname or "Documentation"
    title = tail.replace("-", " ").replace("_", " ").strip()
    return title[:300] or "Documentation"
