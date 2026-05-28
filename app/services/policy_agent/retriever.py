from __future__ import annotations

import json
import math
import re
from pathlib import Path

from app.services.embeddings import Embedder
from app.services.policy_agent.types import RetrievedSource

TOKEN_RE = re.compile(r"[a-z0-9]+")


class HybridPolicyRetriever:
    def __init__(self, documents: list[dict[str, object]], *, embedder: Embedder) -> None:
        self._documents = documents
        self._embedder = embedder

    @classmethod
    def load(cls, index_path: Path, *, embedder: Embedder) -> "HybridPolicyRetriever":
        payload = json.loads(index_path.read_text())
        return cls(payload["documents"], embedder=embedder)

    def search(self, query: str, *, top_k: int = 5) -> list[RetrievedSource]:
        query_terms = _term_freqs(_tokenize(query))
        query_embedding = self._embedder(query)
        results: list[RetrievedSource] = []

        for document in self._documents:
            lexical_score = _lexical_score(query_terms, document["term_freqs"])
            dense_score = _cosine_similarity(query_embedding, document["embedding"])
            hybrid_score = (0.5 * lexical_score) + (0.5 * dense_score)
            if hybrid_score <= 0:
                continue
            results.append(
                RetrievedSource(
                    source_id=str(document["source_id"]),
                    title=str(document["title"]),
                    citation=str(document["citation"]),
                    source_type=str(document["source_type"]),
                    text=str(document["text"]),
                    score=round(hybrid_score, 6),
                )
            )

        return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _term_freqs(tokens: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    return counts


def _lexical_score(query_terms: dict[str, int], document_terms: dict[str, int]) -> float:
    overlap = sum(min(query_terms[token], document_terms.get(token, 0)) for token in query_terms)
    total = sum(query_terms.values()) or 1
    return overlap / total


def _cosine_similarity(query_embedding: list[float], document_embedding: list[float]) -> float:
    dot = sum(q * d for q, d in zip(query_embedding, document_embedding))
    if dot <= 0:
        return 0.0
    query_norm = math.sqrt(sum(q * q for q in query_embedding)) or 1.0
    document_norm = math.sqrt(sum(d * d for d in document_embedding)) or 1.0
    return dot / (query_norm * document_norm)
