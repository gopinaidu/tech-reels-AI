import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from reelagent.intelligence.adapters.openai import (
    OpenAiStructuredLlmClient,
    OpenAiStructuredLlmError,
)


def _client(response_payload: dict[str, object]) -> OpenAiStructuredLlmClient:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.headers["authorization"] == "Bearer test-key"
        assert body["model"] == "test-model"
        assert body["text"]["format"]["type"] == "json_schema"
        assert body["text"]["format"]["strict"] is False
        return httpx.Response(200, json=response_payload)

    return OpenAiStructuredLlmClient(
        api_key=SecretStr("test-key"),
        model="test-model",
        transport=httpx.MockTransport(handler),
    )


def test_returns_parsed_structured_output() -> None:
    client = _client(
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"what_happened":"ok"}',
                        }
                    ],
                }
            ],
        }
    )

    result = asyncio.run(
        client.generate_json(
            system_prompt="system",
            input_payload={"topic": "example"},
            output_schema={"type": "object"},
        )
    )

    assert result == {"what_happened": "ok"}


def test_rejects_model_refusal() -> None:
    client = _client(
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "refusal", "refusal": "cannot comply"}],
                }
            ],
        }
    )

    with pytest.raises(OpenAiStructuredLlmError, match="refused"):
        asyncio.run(
            client.generate_json(
                system_prompt="system",
                input_payload={"topic": "example"},
                output_schema={"type": "object"},
            )
        )


def test_rejects_incomplete_response() -> None:
    client = _client({"status": "incomplete", "output": []})

    with pytest.raises(OpenAiStructuredLlmError, match="did not complete"):
        asyncio.run(
            client.generate_json(
                system_prompt="system",
                input_payload={"topic": "example"},
                output_schema={"type": "object"},
            )
        )
