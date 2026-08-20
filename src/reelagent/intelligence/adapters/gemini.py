from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import SecretStr


class GeminiStructuredLlmError(RuntimeError):
    """Raised when Gemini cannot return usable structured JSON."""


class GeminiStructuredLlmClient:
    """Call Gemini generateContent with JSON-schema constrained output."""

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
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent"
        )
        body = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": json.dumps(input_payload, separators=(",", ":"))}
                    ],
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": output_schema,
            },
        }
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key.get_secret_value(),
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(url, headers=headers, json=body)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            raise GeminiStructuredLlmError("Gemini structured generation failed") from exc

        text = _extract_text(payload)
        try:
            parsed = json.loads(text)
        except (TypeError, ValueError) as exc:
            raise GeminiStructuredLlmError("Gemini returned invalid JSON output") from exc
        if not isinstance(parsed, dict):
            raise GeminiStructuredLlmError("Gemini structured output must be a JSON object")
        return parsed


def _extract_text(payload: Any) -> str:
    if not isinstance(payload, dict):
        raise GeminiStructuredLlmError("Gemini response must be a JSON object")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise GeminiStructuredLlmError("Gemini response is missing candidates")
    first = candidates[0]
    if not isinstance(first, dict):
        raise GeminiStructuredLlmError("Gemini candidate is invalid")
    content = first.get("content")
    if not isinstance(content, dict) or not isinstance(content.get("parts"), list):
        raise GeminiStructuredLlmError("Gemini response is missing content parts")
    for part in content["parts"]:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            return str(part["text"])
    raise GeminiStructuredLlmError("Gemini response is missing output text")
