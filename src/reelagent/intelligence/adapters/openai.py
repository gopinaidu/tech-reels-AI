from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import SecretStr

_OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


class OpenAiStructuredLlmError(RuntimeError):
    """Raised when OpenAI cannot return a usable structured response."""


class OpenAiStructuredLlmClient:
    """Call the OpenAI Responses API for schema-constrained JSON generation."""

    def __init__(
        self,
        *,
        api_key: SecretStr,
        model: str,
        timeout_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = httpx.Timeout(timeout_seconds)
        self._transport = transport

    async def generate_json(
        self,
        *,
        system_prompt: str,
        input_payload: dict[str, Any],
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        request_body = {
            "model": self._model,
            "instructions": system_prompt,
            "input": json.dumps(input_payload, separators=(",", ":")),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "topic_intelligence_brief",
                    "schema": output_schema,
                    "strict": False,
                }
            },
        }
        headers = {
            "Authorization": f"Bearer {self._api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    _OPENAI_RESPONSES_URL,
                    headers=headers,
                    json=request_body,
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            raise OpenAiStructuredLlmError("OpenAI structured generation failed") from exc

        output_text = _extract_output_text(payload)
        try:
            parsed = json.loads(output_text)
        except (TypeError, ValueError) as exc:
            raise OpenAiStructuredLlmError("OpenAI returned invalid JSON output") from exc
        if not isinstance(parsed, dict):
            raise OpenAiStructuredLlmError("OpenAI structured output must be a JSON object")
        return parsed


def _extract_output_text(payload: Any) -> str:
    if not isinstance(payload, dict):
        raise OpenAiStructuredLlmError("OpenAI response must be a JSON object")
    if payload.get("status") not in {None, "completed"}:
        raise OpenAiStructuredLlmError("OpenAI response did not complete successfully")

    output = payload.get("output")
    if not isinstance(output, list):
        raise OpenAiStructuredLlmError("OpenAI response is missing output items")
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "refusal":
                raise OpenAiStructuredLlmError("OpenAI refused Topic Intelligence generation")
            if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                return str(part["text"])
    raise OpenAiStructuredLlmError("OpenAI response is missing output text")
