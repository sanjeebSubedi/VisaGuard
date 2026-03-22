from __future__ import annotations

import json
from typing import Any

from google import genai


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

    def generate_structured(self, *, model: str, prompt: str) -> dict[str, Any]:
        try:
            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
            )
            return json.loads(response.text)
        except GeminiUnavailableError:
            raise
        except Exception as exc:
            raise GeminiResponseError(str(exc)) from exc
