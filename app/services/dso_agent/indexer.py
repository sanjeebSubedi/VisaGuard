from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import chromadb

from app.services.dso_agent.corpus import load_dso_sources

COLLECTION_NAME = 'dso_corpus'
TOKEN_RE = re.compile(r'[a-z0-9]+')
EMBEDDING_DIMS = 256


def build_dso_index(*, federal_sources_dir: Path, university_sources_root: Path, persist_directory: Path) -> Path:
    client = chromadb.PersistentClient(path=str(persist_directory))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(name=COLLECTION_NAME, metadata={'description': 'DSO chat corpus'})
    sources = load_dso_sources(federal_sources_dir=federal_sources_dir, university_sources_root=university_sources_root)
    if sources:
        collection.add(
            ids=[source.source_id for source in sources],
            documents=[source.text for source in sources],
            metadatas=[_build_metadata(source) for source in sources],
            embeddings=[_embed_text(source.text) for source in sources],
        )
    return persist_directory


def _build_metadata(source) -> dict[str, object]:
    tokens = _tokenize(source.text)
    term_freqs: dict[str, int] = {}
    for token in tokens:
        term_freqs[token] = term_freqs.get(token, 0) + 1
    norm = math.sqrt(sum(count * count for count in term_freqs.values())) or 1.0
    return {
        'title': source.title,
        'citation': source.citation,
        'source_type': source.source_type,
        'school_key': source.school_key or '',
        'source_path': source.source_path or '',
        'term_freqs_json': json.dumps(term_freqs, sort_keys=True),
        'norm': norm,
    }


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _embed_text(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMS
    for token in _tokenize(text):
        digest = hashlib.sha256(token.encode()).digest()
        idx = int.from_bytes(digest[:4], 'big') % EMBEDDING_DIMS
        vector[idx] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]
