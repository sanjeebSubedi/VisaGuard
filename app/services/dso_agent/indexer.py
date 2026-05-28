from __future__ import annotations

import json
import re
from pathlib import Path

import chromadb

from app.core.config import Settings
from app.services.dso_agent.corpus import load_dso_sources
from app.services.embeddings import Embedder, build_embedder

COLLECTION_NAME = 'dso_corpus'
TOKEN_RE = re.compile(r'[a-z0-9]+')


def build_dso_index(*, federal_sources_dir: Path, university_sources_root: Path, persist_directory: Path, embedder: Embedder) -> Path:
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
            embeddings=[embedder(source.text) for source in sources],
        )
    return persist_directory


def _build_metadata(source) -> dict[str, object]:
    tokens = _tokenize(source.text)
    term_freqs: dict[str, int] = {}
    for token in tokens:
        term_freqs[token] = term_freqs.get(token, 0) + 1
    return {
        'title': source.title,
        'citation': source.citation,
        'source_type': source.source_type,
        'school_key': source.school_key or '',
        'source_path': source.source_path or '',
        'term_freqs_json': json.dumps(term_freqs, sort_keys=True),
    }


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def main() -> None:
    settings = Settings()
    build_dso_index(
        federal_sources_dir=Path("./data/dso/federal"),
        university_sources_root=Path("./data/dso/universities"),
        persist_directory=Path(settings.dso_index_path),
        embedder=build_embedder(settings),
    )


if __name__ == "__main__":
    main()
