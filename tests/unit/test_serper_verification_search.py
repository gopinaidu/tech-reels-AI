import asyncio
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from reelagent.config import Settings
from reelagent.topics.models import SourceKind
from reelagent.verification.adapters import (
    SerperVerificationSearchClient,
    SerperVerificationSearchError,
)
from reelagent.verification.runtime import (
    VerificationRuntimeConfigurationError,
    build_verification_pipeline,
)


class _StructuredClient:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def generate_json(
        self,
        *,
        system_prompt: str,
        input_payload: dict[str, Any],
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append(input_payload)
        return self.responses.pop(0)


def test_serper_search_uses_free_tier_query_and_keeps_only_trusted_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            assert str(request.url) == "https://google.serper.dev/search"
            assert request.headers["X-API-KEY"] == "serper-secret"
            payload = request.read().decode()
            assert "PostgreSQL" in payload
            assert "skip locked" in payload
            assert "queue" in payload
            assert "documentation" in payload
            assert "site:" not in payload
            return httpx.Response(
                200,
                json={
                    "organic": [
                        {
                            "title": "PostgreSQL SELECT documentation",
                            "link": "https://www.postgresql.org/docs/current/sql-select.html",
                            "snippet": "Official SELECT documentation.",
                            "position": 1,
                        },
                        {
                            "title": "Stack Overflow discussion",
                            "link": "https://stackoverflow.com/questions/example",
                            "snippet": "Community discussion.",
                            "position": 2,
                        },
                    ]
                },
            )
        if str(request.url).endswith("/docs/current/sql-select.html"):
            return httpx.Response(
                200,
                text=(
                    "<html><body>PostgreSQL SELECT locking clauses include SKIP LOCKED. "
                    "It can be useful with multiple consumers accessing a queue-like table."
                    "</body></html>"
                ),
                headers={"content-type": "text/html"},
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    client = SerperVerificationSearchClient(
        api_key=SecretStr("serper-secret"),
        transport=httpx.MockTransport(handler),
    )

    hits = asyncio.run(
        client.search(
            "PostgreSQL supports SKIP LOCKED for queue-style worker coordination.",
            limit=3,
        )
    )

    assert len(hits) == 1
    assert str(hits[0].url).endswith("/docs/current/sql-select.html")
    assert hits[0].source_kind == SourceKind.OFFICIAL
    assert "SKIP LOCKED" in hits[0].snippet


def test_serper_uses_llm_query_and_ranking_after_trust_filter() -> None:
    llm = _StructuredClient(
        [
            {"research_query": "Kafka partition ordering documentation"},
            {"selected_indices": [1, 0]},
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            payload = request.read().decode()
            assert "Kafka partition ordering documentation" in payload
            assert "site:" not in payload
            return httpx.Response(
                200,
                json={
                    "organic": [
                        {
                            "title": "Kafka documentation",
                            "link": "https://kafka.apache.org/documentation/",
                            "snippet": "General Kafka documentation.",
                        },
                        {
                            "title": "Kafka design",
                            "link": "https://kafka.apache.org/41/design/design/",
                            "snippet": "A partition is an ordered sequence of records.",
                        },
                        {
                            "title": "Community answer",
                            "link": "https://stackoverflow.com/questions/example",
                            "snippet": "Kafka ordering discussion.",
                        },
                    ]
                },
            )
        if "/41/design/design/" in str(request.url):
            return httpx.Response(
                200,
                text="<html><body>A partition is an ordered sequence of records.</body></html>",
                headers={"content-type": "text/html"},
            )
        return httpx.Response(
            200,
            text="<html><body>General Kafka documentation.</body></html>",
            headers={"content-type": "text/html"},
        )

    client = SerperVerificationSearchClient(
        api_key=SecretStr("serper-secret"),
        llm_client=llm,
        transport=httpx.MockTransport(handler),
    )

    hits = asyncio.run(
        client.search("Kafka preserves message ordering within a partition.", limit=1)
    )

    assert len(hits) == 1
    assert "/41/design/design/" in str(hits[0].url)
    assert len(llm.calls) == 2
    ranking_candidates = llm.calls[1]["candidates"]
    assert len(ranking_candidates) == 2
    assert all("stackoverflow.com" not in item["url"] for item in ranking_candidates)


def test_serper_llm_failure_falls_back_to_deterministic_query() -> None:
    class _FailingClient:
        async def generate_json(
            self,
            *,
            system_prompt: str,
            input_payload: dict[str, Any],
            output_schema: dict[str, Any],
        ) -> dict[str, Any]:
            raise RuntimeError("temporary model failure")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            payload = request.read().decode()
            assert "PostgreSQL" in payload
            assert "documentation" in payload
            return httpx.Response(
                200,
                json={
                    "organic": [
                        {
                            "title": "SELECT",
                            "link": "https://www.postgresql.org/docs/current/sql-select.html",
                            "snippet": "SKIP LOCKED documentation.",
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            text="<html><body>SKIP LOCKED documentation.</body></html>",
            headers={"content-type": "text/html"},
        )

    client = SerperVerificationSearchClient(
        api_key=SecretStr("serper-secret"),
        llm_client=_FailingClient(),
        transport=httpx.MockTransport(handler),
    )

    hits = asyncio.run(client.search("PostgreSQL SKIP LOCKED", limit=1))

    assert len(hits) == 1


def test_serper_extracts_relevant_window_from_long_official_page() -> None:
    padding = "PostgreSQL documentation navigation and general reference. " * 120
    relevant = (
        "SKIP LOCKED can avoid lock contention with multiple consumers accessing "
        "a queue-like table for worker coordination."
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                200,
                json={
                    "organic": [
                        {
                            "title": "SELECT",
                            "link": "https://www.postgresql.org/docs/current/sql-select.html",
                            "snippet": "SELECT reference.",
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            text=f"<html><body>{padding}{relevant}</body></html>",
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
    assert "SKIP LOCKED" in hits[0].snippet
    assert "worker coordination" in hits[0].snippet
    assert len(hits[0].snippet) <= 2_000


def test_serper_search_returns_empty_without_known_authoritative_domain() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Serper must not be called for an unknown source family")

    client = SerperVerificationSearchClient(
        api_key=SecretStr("serper-secret"),
        transport=httpx.MockTransport(handler),
    )

    assert asyncio.run(client.search("unknown proprietary widget", limit=3)) == ()


def test_serper_search_surfaces_provider_http_error() -> None:
    client = SerperVerificationSearchClient(
        api_key=SecretStr("serper-secret"),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                400,
                json={"message": "Query pattern not allowed for free accounts."},
            )
        ),
    )

    with pytest.raises(
        SerperVerificationSearchError,
        match=r"HTTP 400: Query pattern not allowed for free accounts\.",
    ):
        asyncio.run(client.search("PostgreSQL SKIP LOCKED", limit=1))


def test_runtime_requires_serper_key_for_default_provider() -> None:
    with pytest.raises(VerificationRuntimeConfigurationError, match="SERPER_API_KEY"):
        build_verification_pipeline(
            Settings(
                _env_file=None,
                llm_provider="gemini",
                gemini_api_key=SecretStr("gemini"),
                serper_api_key=SecretStr(""),
            )
        )

    pipeline = build_verification_pipeline(
        Settings(
            _env_file=None,
            llm_provider="gemini",
            gemini_api_key=SecretStr("gemini"),
            serper_api_key=SecretStr("serper"),
        )
    )
    assert pipeline is not None
