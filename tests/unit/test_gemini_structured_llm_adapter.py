import asyncio
import json

import httpx
from pydantic import SecretStr

from reelagent.intelligence.adapters.gemini import GeminiStructuredLlmClient


def test_gemini_structured_client_sends_schema_and_parses_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-goog-api-key"] == "gemini-secret"
        assert request.url.path.endswith("/models/gemini-3.1-flash-lite:generateContent")
        body = json.loads(request.content)
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        assert body["generationConfig"]["responseJsonSchema"]["type"] == "object"
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": '{"verdict":"supported"}'}]}}
                ]
            },
        )

    client = GeminiStructuredLlmClient(
        api_key=SecretStr("gemini-secret"),
        model="gemini-3.1-flash-lite",
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(
        client.generate_json(
            system_prompt="Verify the claim.",
            input_payload={"claim": "example"},
            output_schema={"type": "object", "properties": {"verdict": {"type": "string"}}},
        )
    )

    assert result == {"verdict": "supported"}
