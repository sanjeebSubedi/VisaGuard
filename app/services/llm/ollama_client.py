from __future__ import annotations

from ollama import Client


class OllamaUnavailableError(RuntimeError):
    pass


class OllamaClientAdapter:
    def __init__(self, host: str, timeout_seconds: int) -> None:
        try:
            self._client = Client(host=host, timeout=timeout_seconds)
        except Exception as exc:
            raise OllamaUnavailableError(str(exc)) from exc

    def generate(self, *, model: str, prompt: str) -> str:
        try:
            response = self._client.generate(model=model, prompt=prompt)
        except Exception as exc:
            raise OllamaUnavailableError(str(exc)) from exc
        return response["response"]
