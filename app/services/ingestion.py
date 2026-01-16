"""
Document Ingestion Service

Handles PDF parsing using LlamaParse with content-addressable caching (SHA-256)
to avoid re-parsing the same documents and save API costs.

Key principles:
- Hash first, parse only if needed, store results
- NEVER persist raw_text (with PII) to disk - only scrubbed_text is cached
- Use markdown mode for table preservation in forms
"""

import hashlib
import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from app.core.config import DATA_DIR, LLAMA_CLOUD_API_KEY
from app.privacy.pipeline import get_privacy_pipeline


class ParsedDocument(BaseModel):
    """Structured representation of a parsed document."""
    
    document_id: str = Field(description="SHA-256 hash of the original file")
    original_filename: str
    content_hash: str
    raw_text: str = Field(
        default="",
        description="Full extracted text (in-memory only, NEVER persisted to disk)",
        exclude=True  # Exclude from serialization to prevent PII leakage
    )
    scrubbed_text: str = Field(description="Text with PII removed (safe to persist)")
    extracted_fields: dict = Field(default_factory=dict, description="Structured data extracted from document")
    metadata: dict = Field(default_factory=dict)


class IngestionService:
    """
    Document ingestion with content-addressable caching.
    
    Usage:
        service = IngestionService()
        doc = service.ingest_pdf(Path("path/to/document.pdf"))
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        use_cache: bool = True
    ):
        """
        Initialize the ingestion service.
        
        Args:
            cache_dir: Directory for caching parsed documents.
            use_cache: Whether to use caching (disable for testing).
        """
        self.cache_dir = cache_dir or (DATA_DIR / ".cache" / "parsed")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.use_cache = use_cache
        self.privacy_pipeline = get_privacy_pipeline()
    
    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file for content addressing."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def get_cache_path(self, content_hash: str) -> Path:
        """Get the cache file path for a given content hash."""
        return self.cache_dir / f"{content_hash}.json"
    
    def load_from_cache(self, content_hash: str) -> Optional[ParsedDocument]:
        """Load a previously parsed document from cache."""
        if not self.use_cache:
            return None
        
        cache_path = self.get_cache_path(content_hash)
        if cache_path.exists():
            with open(cache_path, "r") as f:
                data = json.load(f)
                return ParsedDocument(**data)
        return None
    
    def save_to_cache(self, doc: ParsedDocument) -> None:
        """Save a parsed document to cache."""
        if not self.use_cache:
            return
        
        cache_path = self.get_cache_path(doc.content_hash)
        with open(cache_path, "w") as f:
            json.dump(doc.model_dump(), f, indent=2)
    
    def parse_with_llamaparse(self, file_path: Path) -> str:
        """
        Parse a PDF using LlamaParse.
        
        Returns the extracted content in markdown format (preserves tables).
        """
        if not LLAMA_CLOUD_API_KEY:
            raise ValueError(
                "LLAMA_CLOUD_API_KEY not set. "
                "Please configure it in your .env file."
            )
        
        # Import here to avoid loading if not needed
        from llama_parse import LlamaParse
        
        parser = LlamaParse(
            api_key=LLAMA_CLOUD_API_KEY,
            result_type="markdown",  # Preserve table structure for forms
            verbose=False,
        )
        
        # Parse the document
        documents = parser.load_data(str(file_path))
        
        # Combine all pages
        full_text = "\n\n".join([doc.text for doc in documents])
        return full_text
    
    def ingest_pdf(
        self,
        file_path: Path,
        extract_fields: bool = True
    ) -> ParsedDocument:
        """
        Ingest a PDF document with caching and privacy scrubbing.
        
        Process:
        1. Compute SHA-256 hash
        2. Check cache for existing parse
        3. If not cached, parse with LlamaParse
        4. Apply privacy scrubbing
        5. Cache the result
        
        Args:
            file_path: Path to the PDF file.
            extract_fields: Whether to attempt structured field extraction.
            
        Returns:
            ParsedDocument with both raw and scrubbed text.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Step 1: Compute hash
        content_hash = self.compute_file_hash(file_path)
        
        # Step 2: Check cache
        cached = self.load_from_cache(content_hash)
        if cached:
            return cached
        
        # Step 3: Parse document
        raw_text = self.parse_with_llamaparse(file_path)
        
        # Step 4: Apply privacy scrubbing
        scrubbed_text = self.privacy_pipeline.scrub(raw_text)
        
        # Step 5: Create document record
        doc = ParsedDocument(
            document_id=content_hash[:16],  # Short ID for convenience
            original_filename=file_path.name,
            content_hash=content_hash,
            raw_text=raw_text,
            scrubbed_text=scrubbed_text,
            extracted_fields={},  # Will be populated by DocumentAgent
            metadata={
                "file_size_bytes": file_path.stat().st_size,
                "parse_method": "llamaparse",
            }
        )
        
        # Step 6: Cache the result
        self.save_to_cache(doc)
        
        return doc
    
    def ingest_text(self, text: str, source_name: str = "manual_input") -> ParsedDocument:
        """
        Ingest raw text directly (for testing or non-PDF sources).
        
        Applies privacy scrubbing but no caching.
        """
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        scrubbed_text = self.privacy_pipeline.scrub(text)
        
        return ParsedDocument(
            document_id=content_hash[:16],
            original_filename=source_name,
            content_hash=content_hash,
            raw_text=text,
            scrubbed_text=scrubbed_text,
            extracted_fields={},
            metadata={"parse_method": "direct_text"}
        )


# Singleton instance
_service: Optional[IngestionService] = None


def get_ingestion_service() -> IngestionService:
    """Get or create the global ingestion service instance."""
    global _service
    if _service is None:
        _service = IngestionService()
    return _service
