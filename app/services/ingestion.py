"""
Document ingestion with Docling + privacy scrubbing.

Caching stores only scrubbed content to avoid persisting PII.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.privacy.pipeline import PrivacyPipeline
from app.services.ingest_docling import ingest_document


@dataclass
class ParsedDocument:
    document_id: str
    original_filename: str
    content_hash: str
    raw_text: str | None
    scrubbed_text: str
    extracted_fields: dict[str, Any]
    metadata: dict[str, Any]


class IngestionService:
    """Ingest documents to text, scrub PII, and cache safely."""

    def __init__(
        self,
        cache_dir: str | Path = "data/.cache/parsed",
        use_cache: bool = True,
        use_llm_redaction: bool = False,
        llm_model: str | None = None,
    ):
        self.cache_dir = Path(cache_dir)
        self.use_cache = use_cache
        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.privacy = PrivacyPipeline(
            use_llm=use_llm_redaction,
            llm_model=llm_model,
        )

    def compute_file_hash(self, file_path: str | Path) -> str:
        """Compute SHA-256 hash for a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def save_to_cache(self, doc: ParsedDocument) -> None:
        """Persist scrubbed content only (no raw_text)."""
        if not self.use_cache:
            return
        data = {
            "document_id": doc.document_id,
            "original_filename": doc.original_filename,
            "content_hash": doc.content_hash,
            "scrubbed_text": doc.scrubbed_text,
            "extracted_fields": doc.extracted_fields,
            "metadata": doc.metadata,
        }
        cache_path = self._cache_path(doc.content_hash)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_from_cache(self, content_hash: str) -> ParsedDocument | None:
        """Load a scrubbed-only document from cache."""
        cache_path = self._cache_path(content_hash)
        if not cache_path.exists():
            return None
        with open(cache_path, "r") as f:
            data = json.load(f)
        return ParsedDocument(
            document_id=data["document_id"],
            original_filename=data.get("original_filename", ""),
            content_hash=data["content_hash"],
            raw_text=None,
            scrubbed_text=data.get("scrubbed_text", ""),
            extracted_fields=data.get("extracted_fields", {}),
            metadata=data.get("metadata", {}),
        )

    def ingest_text(self, text: str) -> ParsedDocument:
        """Ingest raw text directly and scrub PII."""
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        document_id = content_hash[:16]
        scrubbed_text = self.privacy.scrub(text)
        doc = ParsedDocument(
            document_id=document_id,
            original_filename="text_input",
            content_hash=content_hash,
            raw_text=text,
            scrubbed_text=scrubbed_text,
            extracted_fields={},
            metadata={"source": "text"},
        )
        self.save_to_cache(doc)
        return doc

    def ingest_file(self, file_path: str | Path, doc_type: str | None = None, require_raw_text: bool = True) -> ParsedDocument:
        """Parse a file, scrub PII, and return a ParsedDocument."""
        file_path = Path(file_path)
        content_hash = self.compute_file_hash(file_path)

        cached = self.load_from_cache(content_hash) if self.use_cache else None
        if cached and not require_raw_text:
            return cached

        raw_text = ingest_document(str(file_path))
        scrubbed_text = self.privacy.scrub(raw_text)
        doc = ParsedDocument(
            document_id=content_hash[:16],
            original_filename=file_path.name,
            content_hash=content_hash,
            raw_text=raw_text,
            scrubbed_text=scrubbed_text,
            extracted_fields={},
            metadata={
                "file_size_bytes": file_path.stat().st_size,
                "parse_method": "docling",
                "doc_type": doc_type,
            },
        )
        self.save_to_cache(doc)
        return doc

    def _cache_path(self, content_hash: str) -> Path:
        return self.cache_dir / f"{content_hash}.json"
