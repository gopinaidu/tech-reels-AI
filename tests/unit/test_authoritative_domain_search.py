import asyncio

import httpx

from reelagent.topics.models import SourceKind
from reelagent.verification.adapters.domains import (
    AuthoritativeDomain,
    AuthoritativeDomainSearchClient,
)


def test_authoritative_domain_search_uses_curated_sitemap_and_pages() -> None:
    sitemap = """<?xml version='1.0' encoding='UTF-8'?>
    <urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
      <url><loc>https://docs.example.com/postgresql/skip-locked.html</loc></url>
      <url><loc>https://docs.example.com/postgresql/jsonb.html</loc></url>
    </urlset>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://docs.example.com/sitemap.xml":
            return httpx.Response(200, text=sitemap)
        if str(request.url).endswith("skip-locked.html"):
            return httpx.Response(
                200,
                text="<html><body>SKIP LOCKED supports queue-like access.</body></html>",
                headers={"content-type": "text/html"},
            )
        return httpx.Response(
            200,
            text="<html><body>JSONB documentation.</body></html>",
            headers={"content-type": "text/html"},
        )

    domain = AuthoritativeDomain(
        name="Example Postgres Docs",
        hosts=("docs.example.com",),
        keywords=("postgresql", "skip locked"),
        sitemap_urls=("https://docs.example.com/sitemap.xml",),
    )
    client = AuthoritativeDomainSearchClient(
        domains=(domain,),
        transport=httpx.MockTransport(handler),
    )

    hits = asyncio.run(client.search("PostgreSQL SKIP LOCKED queue", limit=1))

    assert len(hits) == 1
    assert str(hits[0].url).endswith("skip-locked.html")
    assert hits[0].source_kind == SourceKind.OFFICIAL
    assert "queue-like" in hits[0].snippet


def test_authoritative_search_prefers_official_site_search_results() -> None:
    search_html = """
    <html><body>
      <a href="/about/news/postgresql-release.html">News</a>
      <a href="/docs/current/sql-select.html">SELECT documentation</a>
    </body></html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.startswith("https://www.example.com/search/"):
            return httpx.Response(200, text=search_html)
        if url.endswith("/docs/current/sql-select.html"):
            return httpx.Response(
                200,
                text=(
                    "<html><body>SKIP LOCKED can avoid lock contention with multiple "
                    "consumers accessing a queue-like table.</body></html>"
                ),
                headers={"content-type": "text/html"},
            )
        raise AssertionError(f"unexpected request: {url}")

    domain = AuthoritativeDomain(
        name="Example PostgreSQL",
        hosts=("www.example.com",),
        keywords=("postgresql", "skip locked"),
        sitemap_urls=("https://www.example.com/sitemap.xml",),
        search_url_template="https://www.example.com/search/?q={query}",
    )
    client = AuthoritativeDomainSearchClient(
        domains=(domain,),
        transport=httpx.MockTransport(handler),
    )

    hits = asyncio.run(client.search("PostgreSQL SKIP LOCKED queue", limit=1))

    assert len(hits) == 1
    assert str(hits[0].url).endswith("/docs/current/sql-select.html")
    assert "queue-like" in hits[0].snippet


def test_authoritative_search_falls_back_to_sitemap_when_site_search_fails() -> None:
    sitemap = """<?xml version='1.0' encoding='UTF-8'?>
    <urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
      <url><loc>https://www.example.com/docs/current/sql-select.html</loc></url>
    </urlset>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.startswith("https://www.example.com/search/"):
            return httpx.Response(503)
        if url == "https://www.example.com/sitemap.xml":
            return httpx.Response(200, text=sitemap)
        return httpx.Response(
            200,
            text="<html><body>SELECT locking documentation.</body></html>",
            headers={"content-type": "text/html"},
        )

    domain = AuthoritativeDomain(
        name="Example PostgreSQL",
        hosts=("www.example.com",),
        keywords=("postgresql",),
        sitemap_urls=("https://www.example.com/sitemap.xml",),
        search_url_template="https://www.example.com/search/?q={query}",
    )
    client = AuthoritativeDomainSearchClient(
        domains=(domain,),
        transport=httpx.MockTransport(handler),
    )

    hits = asyncio.run(client.search("PostgreSQL SELECT", limit=1))

    assert len(hits) == 1
    assert "/docs/current/sql-select.html" in str(hits[0].url)


def test_authoritative_search_prefers_docs_over_news() -> None:
    sitemap = """<?xml version='1.0' encoding='UTF-8'?>
    <urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
      <url><loc>https://www.example.com/about/news/postgresql-release.html</loc></url>
      <url><loc>https://www.example.com/docs/current/sql-select.html</loc></url>
    </urlset>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://www.example.com/sitemap.xml":
            return httpx.Response(200, text=sitemap)
        if "/docs/" in str(request.url):
            body = "SKIP LOCKED avoids contention for consumers accessing a queue-like table."
        else:
            body = "PostgreSQL community release news."
        return httpx.Response(
            200,
            text=f"<html><body>{body}</body></html>",
            headers={"content-type": "text/html"},
        )

    domain = AuthoritativeDomain(
        name="Example PostgreSQL",
        hosts=("www.example.com",),
        keywords=("postgresql", "skip locked"),
        sitemap_urls=("https://www.example.com/sitemap.xml",),
    )
    client = AuthoritativeDomainSearchClient(
        domains=(domain,),
        transport=httpx.MockTransport(handler),
    )

    hits = asyncio.run(client.search("PostgreSQL SKIP LOCKED queue", limit=1))

    assert len(hits) == 1
    assert "/docs/current/sql-select.html" in str(hits[0].url)
    assert "queue-like" in hits[0].snippet


def test_authoritative_domain_search_caps_long_page_snippets() -> None:
    sitemap = """<?xml version='1.0' encoding='UTF-8'?>
    <urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
      <url><loc>https://docs.example.com/postgresql/skip-locked.html</loc></url>
    </urlset>
    """
    long_body = "SKIP LOCKED queue worker " + ("documentation " * 400)

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://docs.example.com/sitemap.xml":
            return httpx.Response(200, text=sitemap)
        return httpx.Response(
            200,
            text=f"<html><body>{long_body}</body></html>",
            headers={"content-type": "text/html"},
        )

    domain = AuthoritativeDomain(
        name="Example Postgres Docs",
        hosts=("docs.example.com",),
        keywords=("postgresql", "skip locked"),
        sitemap_urls=("https://docs.example.com/sitemap.xml",),
    )
    client = AuthoritativeDomainSearchClient(
        domains=(domain,),
        transport=httpx.MockTransport(handler),
    )

    hits = asyncio.run(client.search("PostgreSQL SKIP LOCKED queue", limit=1))

    assert len(hits) == 1
    assert len(hits[0].snippet) == 2_000


def test_authoritative_domain_search_returns_empty_for_unknown_technology() -> None:
    client = AuthoritativeDomainSearchClient(
        domains=(),
        transport=httpx.MockTransport(lambda request: httpx.Response(500)),
    )

    assert asyncio.run(client.search("unknown proprietary widget", limit=3)) == ()
