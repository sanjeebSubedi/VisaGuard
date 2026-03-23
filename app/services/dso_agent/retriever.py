from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb

from app.services.dso_agent.indexer import COLLECTION_NAME, EMBEDDING_DIMS
from app.services.dso_agent.types import DSOCitation

TOKEN_RE = re.compile(r'[a-z0-9]+')


@dataclass(slots=True)
class _Document:
    source_id: str
    title: str
    citation: str
    source_type: str
    school_key: str | None
    text: str
    term_freqs: dict[str, int]
    norm: float
    embedding_score: float = 0.0


class HybridDSORetriever:
    def __init__(self, documents: list[_Document]) -> None:
        self._documents = documents

    @classmethod
    def from_documents(cls, documents: list[dict[str, Any]]) -> 'HybridDSORetriever':
        built = []
        for document in documents:
            tokens = _tokenize(str(document['text']))
            term_freqs: dict[str, int] = {}
            for token in tokens:
                term_freqs[token] = term_freqs.get(token, 0) + 1
            norm = math.sqrt(sum(v * v for v in term_freqs.values())) or 1.0
            built.append(_Document(
                source_id=str(document['source_id']),
                title=str(document.get('title', document['source_id'])),
                citation=str(document.get('citation', document['source_id'])),
                source_type=str(document['source_type']),
                school_key=document.get('school_key'),
                text=str(document['text']),
                term_freqs=term_freqs,
                norm=norm,
            ))
        return cls(built)

    @classmethod
    def load(cls, *, persist_directory: Path) -> 'HybridDSORetriever':
        client = chromadb.PersistentClient(path=str(persist_directory))
        collection = client.get_collection(COLLECTION_NAME)
        payload = collection.get(include=['documents', 'metadatas', 'embeddings'])
        documents: list[_Document] = []
        for doc_id, text, meta in zip(payload['ids'], payload['documents'], payload['metadatas']):
            documents.append(_Document(
                source_id=str(doc_id),
                title=str(meta['title']),
                citation=str(meta['citation']),
                source_type=str(meta['source_type']),
                school_key=(str(meta.get('school_key')) or None),
                text=str(text),
                term_freqs=json.loads(str(meta['term_freqs_json'])),
                norm=float(meta['norm']),
            ))
        return cls(documents)

    def search(self, query: str, *, scope: str, school_key: str | None, top_k: int = 5) -> list[DSOCitation]:
        query_terms = _term_freqs(_tokenize(query))
        query_norm = math.sqrt(sum(v * v for v in query_terms.values())) or 1.0
        filtered = self._filter_documents(scope=scope, school_key=school_key)
        scored: list[DSOCitation] = []
        for document in filtered:
            lexical = _lexical_score(query_terms, document.term_freqs)
            vector = _cosine_score(query_terms, query_norm, document.term_freqs, document.norm)
            score = (0.5 * lexical) + (0.5 * vector)
            if score <= 0:
                continue
            scored.append(DSOCitation(
                title=document.title,
                citation=document.citation,
                source_type=document.source_type,  # type: ignore[arg-type]
                excerpt=document.text,
                score=round(score, 6),
            ))
        return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]

    def _filter_documents(self, *, scope: str, school_key: str | None) -> list[_Document]:
        if scope == 'federal':
            return [doc for doc in self._documents if doc.source_type == 'federal']
        if scope == 'university':
            return [doc for doc in self._documents if doc.source_type == 'university' and doc.school_key == school_key]
        if scope == 'mixed':
            return [doc for doc in self._documents if doc.source_type == 'federal' or (doc.source_type == 'university' and doc.school_key == school_key)]
        raise ValueError(f'Unsupported scope: {scope}')


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


def _cosine_score(query_terms: dict[str, int], query_norm: float, document_terms: dict[str, int], document_norm: float) -> float:
    dot = sum(query_terms[token] * document_terms.get(token, 0) for token in query_terms)
    if dot <= 0:
        return 0.0
    return dot / (query_norm * document_norm)
