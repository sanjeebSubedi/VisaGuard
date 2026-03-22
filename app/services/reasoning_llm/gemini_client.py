from __future__ import annotations

from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel


class GeminiUnavailableError(RuntimeError):
    pass


class GeminiResponseError(RuntimeError):
    pass


class GeminiReasoningClient:
    def __init__(self, api_key: str | None) -> None:
        if not api_key:
            raise GeminiUnavailableError("Missing GEMINI_API_KEY")
        try:
            self._client = genai.Client(api_key=api_key)
        except Exception as exc:
            raise GeminiUnavailableError(str(exc)) from exc

    def generate_structured(self, *, model: str, prompt: str, schema: Any) -> dict[str, Any]:
        try:
            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            parsed = getattr(response, "parsed", None)
            if isinstance(parsed, BaseModel):
                return parsed.model_dump()
            if isinstance(parsed, dict):
                return parsed
            raise GeminiResponseError("Gemini returned malformed structured output")
        except GeminiUnavailableError:
            raise
        except Exception as exc:
            raise GeminiResponseError(str(exc)) from exc
