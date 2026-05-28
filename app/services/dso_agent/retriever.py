from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import chromadb

from app.services.dso_agent.indexer import COLLECTION_NAME
from app.services.dso_agent.types import DSOCitation
from app.services.embeddings import Embedder

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
    embedding: list[float] = field(default_factory=list)


class HybridDSORetriever:
    def __init__(self, documents: list[_Document], *, embedder: Embedder) -> None:
        self._documents = documents
        self._embedder = embedder

    @classmethod
    def from_documents(cls, documents: list[dict[str, Any]], *, embedder: Embedder) -> 'HybridDSORetriever':
        built = []
        for document in documents:
            text = str(document['text'])
            built.append(_Document(
                source_id=str(document['source_id']),
                title=str(document.get('title', document['source_id'])),
                citation=str(document.get('citation', document['source_id'])),
                source_type=str(document['source_type']),
                school_key=document.get('school_key'),
                text=text,
                term_freqs=_term_freqs(_tokenize(text)),
                embedding=embedder(text),
            ))
        return cls(built, embedder=embedder)

    @classmethod
    def load(cls, *, persist_directory: Path, embedder: Embedder) -> 'HybridDSORetriever':
        client = chromadb.PersistentClient(path=str(persist_directory))
        collection = client.get_collection(COLLECTION_NAME)
        payload = collection.get(include=['documents', 'metadatas', 'embeddings'])
        documents: list[_Document] = []
        for doc_id, text, meta, embedding in zip(payload['ids'], payload['documents'], payload['metadatas'], payload['embeddings']):
            documents.append(_Document(
                source_id=str(doc_id),
                title=str(meta['title']),
                citation=str(meta['citation']),
                source_type=str(meta['source_type']),
                school_key=(str(meta.get('school_key')) or None),
                text=str(text),
                term_freqs=json.loads(str(meta['term_freqs_json'])),
                embedding=[float(value) for value in embedding],
            ))
        return cls(documents, embedder=embedder)

    def search(self, query: str, *, scope: str, school_key: str | None, top_k: int = 5) -> list[DSOCitation]:
        query_terms = _term_freqs(_tokenize(query))
        query_embedding = self._embedder(query)
        filtered = self._filter_documents(scope=scope, school_key=school_key)
        scored: list[DSOCitation] = []
        for document in filtered:
            lexical = _lexical_score(query_terms, document.term_freqs)
            dense = _cosine_similarity(query_embedding, document.embedding)
            score = (0.5 * lexical) + (0.5 * dense)
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


def _cosine_similarity(query_embedding: list[float], document_embedding: list[float]) -> float:
    dot = sum(q * d for q, d in zip(query_embedding, document_embedding))
    if dot <= 0:
        return 0.0
    query_norm = math.sqrt(sum(q * q for q in query_embedding)) or 1.0
    document_norm = math.sqrt(sum(d * d for d in document_embedding)) or 1.0
    return dot / (query_norm * document_norm)
