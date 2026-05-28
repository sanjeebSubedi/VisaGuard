from __future__ import annotations

from collections.abc import Callable

from app.core.config import Settings
from app.services.llm.ollama_client import OllamaClientAdapter

Embedder = Callable[[str], list[float]]


class OllamaEmbedder:
    def __init__(self, *, host: str, model: str, timeout_seconds: int) -> None:
        self._client = OllamaClientAdapter(host=host, timeout_seconds=timeout_seconds)
        self._model = model

    def __call__(self, text: str) -> list[float]:
        return self._client.embed(model=self._model, text=text)


def build_embedder(settings: Settings) -> OllamaEmbedder:
    return OllamaEmbedder(
        host=settings.ollama_host,
        model=settings.ollama_embedding_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
