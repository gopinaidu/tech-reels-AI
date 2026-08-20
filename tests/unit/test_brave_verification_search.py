import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from reelagent.config import Settings
from reelagent.intelligence.llm_runtime import LlmRuntimeConfigurationError
from reelagent.topics.models import SourceKind
from reelagent.verification.adapters import BraveVerificationSearchClient
from reelagent.verification.runtime import (
    VerificationRuntimeConfigurationError,
    build_verification_pipeline,
)


def test_brave_search_maps_web_results_and_authenticates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Subscription-Token"] == "brave-secret"
        assert request.url.params["q"] == "PostgreSQL SKIP LOCKED"
        assert request.url.params["count"] == "2"
        payload = {
            "web": {
                "results": [
                    {
                        "title": "PostgreSQL SELECT documentation",
                        "url": "https://www.postgresql.org/docs/current/sql-select.html",
                        "description": "SKIP LOCKED can be used for queue-like tables.",
                    },
                    {
                        "title": "Example engineering article",
                        "url": "https://engineering.example.com/postgres-queues",
                        "description": "An engineering discussion of queues.",
                    },
                ]
            }
        }
        return httpx.Response(200, content=json.dumps(payload).encode())

    client = BraveVerificationSearchClient(
        api_key=SecretStr("brave-secret"),
        transport=httpx.MockTransport(handler),
    )

    hits = asyncio.run(client.search("PostgreSQL SKIP LOCKED", limit=2))

    assert len(hits) == 2
    assert hits[0].source_kind == SourceKind.OFFICIAL
    assert hits[1].source_kind == SourceKind.ENGINEERING_BLOG


def test_brave_search_handles_missing_web_results() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"type": "search"}))
    client = BraveVerificationSearchClient(
        api_key=SecretStr("brave-secret"),
        transport=transport,
    )

    assert asyncio.run(client.search("claim", limit=1)) == ()


def test_runtime_requires_gemini_key_when_search_is_configured() -> None:
    settings = Settings(
        _env_file=None,
        llm_provider="gemini",
        gemini_api_key=None,
        serper_api_key=SecretStr("serper"),
    )
    with pytest.raises(LlmRuntimeConfigurationError, match="GEMINI_API_KEY"):
        build_verification_pipeline(settings)


def test_runtime_requires_brave_key_only_for_brave_provider() -> None:
    with pytest.raises(VerificationRuntimeConfigurationError, match="BRAVE_SEARCH_API_KEY"):
        build_verification_pipeline(
            Settings(
                _env_file=None,
                llm_provider="gemini",
                gemini_api_key=SecretStr("gemini"),
                brave_search_api_key=SecretStr(""),
                verification_search_provider="brave",
            )
        )

    pipeline = build_verification_pipeline(
        Settings(
            _env_file=None,
            llm_provider="gemini",
            gemini_api_key=SecretStr("gemini"),
            brave_search_api_key=SecretStr("brave"),
            verification_search_provider="brave",
        )
    )
    assert pipeline is not None
