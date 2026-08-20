import asyncio

import httpx
from pydantic import SecretStr

from reelagent.verification.adapters import SerperVerificationSearchClient


def test_serper_preserves_search_snippet_when_page_excerpt_is_weaker() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                200,
                json={
                    "organic": [
                        {
                            "title": "PostgreSQL SELECT documentation",
                            "link": "https://www.postgresql.org/docs/current/sql-select.html",
                            "snippet": (
                                "With SKIP LOCKED, selected rows that cannot be immediately "
                                "locked are skipped."
                            ),
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            text="<html><body>LIMIT and OFFSET syntax reference.</body></html>",
            headers={"content-type": "text/html"},
        )

    client = SerperVerificationSearchClient(
        api_key=SecretStr("serper-secret"),
        transport=httpx.MockTransport(handler),
    )

    hits = asyncio.run(
        client.search(
            "PostgreSQL supports SKIP LOCKED for queue-style worker coordination.",
            limit=1,
        )
    )

    assert len(hits) == 1
    assert "With SKIP LOCKED" in hits[0].snippet
    assert "LIMIT and OFFSET" in hits[0].snippet
    assert len(hits[0].snippet) <= 2_000


def test_serper_uses_search_snippet_when_official_page_fetch_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                200,
                json={
                    "organic": [
                        {
                            "title": "Python threading documentation",
                            "link": "https://docs.python.org/3/library/threading.html",
                            "snippet": (
                                "The GIL means only one thread can execute Python bytecode "
                                "at a time."
                            ),
                        }
                    ]
                },
            )
        return httpx.Response(503)

    client = SerperVerificationSearchClient(
        api_key=SecretStr("serper-secret"),
        transport=httpx.MockTransport(handler),
    )

    hits = asyncio.run(
        client.search("CPython GIL limits concurrent Python bytecode execution.", limit=1)
    )

    assert len(hits) == 1
    assert "only one thread can execute Python bytecode" in hits[0].snippet
