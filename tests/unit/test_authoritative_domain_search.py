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


def test_authoritative_domain_search_returns_empty_for_unknown_technology() -> None:
    client = AuthoritativeDomainSearchClient(
        domains=(),
        transport=httpx.MockTransport(lambda request: httpx.Response(500)),
    )

    assert asyncio.run(client.search("unknown proprietary widget", limit=3)) == ()
