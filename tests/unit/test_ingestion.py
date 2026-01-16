"""
Tests for Document Ingestion Service
"""

import hashlib
from pathlib import Path
import pytest


class TestIngestionService:
    """Tests for document ingestion with caching."""

    def test_compute_file_hash(self, tmp_path):
        """File hash should be deterministic."""
        from app.services.ingestion import IngestionService
        
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")
        
        service = IngestionService(cache_dir=tmp_path / "cache")
        
        hash1 = service.compute_file_hash(test_file)
        hash2 = service.compute_file_hash(test_file)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64 hex characters

    def test_different_files_different_hashes(self, tmp_path):
        """Different files should produce different hashes."""
        from app.services.ingestion import IngestionService
        
        file1 = tmp_path / "file1.txt"
        file1.write_text("Content A")
        
        file2 = tmp_path / "file2.txt"
        file2.write_text("Content B")
        
        service = IngestionService(cache_dir=tmp_path / "cache")
        
        hash1 = service.compute_file_hash(file1)
        hash2 = service.compute_file_hash(file2)
        
        assert hash1 != hash2

    def test_cache_save_and_load(self, tmp_path):
        """Parsed documents should be cached and retrievable."""
        from app.services.ingestion import IngestionService, ParsedDocument
        
        service = IngestionService(cache_dir=tmp_path / "cache")
        
        doc = ParsedDocument(
            document_id="abc123",
            original_filename="test.pdf",
            content_hash="fakehash123",
            raw_text="Raw content with SSN 123-45-6789",  # This should NOT be persisted
            scrubbed_text="Raw content with SSN [SSN_REDACTED]",
            extracted_fields={"name": "John"},
            metadata={"source": "test"}
        )
        
        service.save_to_cache(doc)
        loaded = service.load_from_cache("fakehash123")
        
        assert loaded is not None
        assert loaded.document_id == "abc123"
        assert loaded.scrubbed_text == "Raw content with SSN [SSN_REDACTED]"

    def test_raw_text_not_persisted_to_cache(self, tmp_path):
        """CRITICAL: raw_text (containing PII) must NEVER be written to disk."""
        import json
        from app.services.ingestion import IngestionService, ParsedDocument
        
        service = IngestionService(cache_dir=tmp_path / "cache")
        
        doc = ParsedDocument(
            document_id="abc123",
            original_filename="test.pdf",
            content_hash="privacytest123",
            raw_text="SECRET SSN 999-88-7777 MUST NOT BE SAVED",
            scrubbed_text="SECRET SSN [REDACTED] MUST NOT BE SAVED",
            extracted_fields={},
            metadata={}
        )
        
        service.save_to_cache(doc)
        
        # Read the cache file directly and verify raw_text is NOT there
        cache_file = tmp_path / "cache" / "privacytest123.json"
        with open(cache_file, "r") as f:
            cached_data = json.load(f)
        
        # raw_text should be excluded from serialization
        assert "raw_text" not in cached_data
        assert "999-88-7777" not in str(cached_data)
        # But scrubbed_text should be there
        assert cached_data["scrubbed_text"] == "SECRET SSN [REDACTED] MUST NOT BE SAVED"

    def test_cache_miss_returns_none(self, tmp_path):
        """Loading non-existent cache should return None."""
        from app.services.ingestion import IngestionService
        
        service = IngestionService(cache_dir=tmp_path / "cache")
        
        result = service.load_from_cache("nonexistent_hash")
        
        assert result is None

    def test_ingest_text_applies_privacy_scrubbing(self, tmp_path):
        """Direct text ingestion should apply privacy scrubbing."""
        from app.services.ingestion import IngestionService
        
        service = IngestionService(cache_dir=tmp_path / "cache", use_cache=False)
        
        text = "Contact john@example.com for info"
        doc = service.ingest_text(text)
        
        assert "john@example.com" in doc.raw_text
        assert "john@example.com" not in doc.scrubbed_text
        assert "[EMAIL]" in doc.scrubbed_text

    def test_ingest_text_generates_hash(self, tmp_path):
        """Text ingestion should generate content hash."""
        from app.services.ingestion import IngestionService
        
        service = IngestionService(cache_dir=tmp_path / "cache", use_cache=False)
        
        text = "Sample document content"
        doc = service.ingest_text(text)
        
        expected_hash = hashlib.sha256(text.encode()).hexdigest()
        
        assert doc.content_hash == expected_hash
        assert doc.document_id == expected_hash[:16]
