"""
Document Ingestion Service

Handles PDF parsing using LlamaParse with content-addressable caching (SHA-256)
to avoid re-parsing the same documents and save API costs.

Key principles:
- Hash first, parse only if needed, store results
- NEVER persist raw_text (with PII) to disk - only scrubbed_text is cached
- Use markdown mode for table preservation in forms

IMPORTANT - Form Filling Paradox:
- We scrub PII before storing, but we need real data (names, IDs) to fill forms later.
- Solution: extracted_fields (containing real values) must be extracted BEFORE scrubbing.
- The extracted_fields are stored SEPARATELY (encrypted in Postgres in production).
- The scrubbed_text goes to the Vector DB for RAG queries.
- This gives us: privacy-preserving RAG + real data for form filling.
"""

import hashlib
import json
from typing import Optional, Callable

from pydantic import BaseModel, Field

from app.core.config import DATA_DIR, LLAMA_CLOUD_API_KEY
from app.privacy.pipeline import get_privacy_pipeline


# Type alias for field extraction function
FieldExtractor = Callable[[str], dict]

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
    scrubbed_text: str = Field(description="Text with PII removed (safe for Vector DB)")
    extracted_fields: dict = Field(
        default_factory=dict, 
        description="Structured data extracted BEFORE scrubbing (contains real values for form filling)",
        exclude=True  # Also exclude - this goes to encrypted DB, not cache file
    )
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
        field_extractor: Optional[FieldExtractor] = None,
    ) -> ParsedDocument:
        """
        Ingest a PDF document with caching and privacy scrubbing.
        
        CRITICAL ARCHITECTURE NOTE:
        If you need to fill forms later (with real PII values), you MUST provide
        a field_extractor callback. This extracts structured data BEFORE scrubbing.
        The extracted_fields (with real values) should be stored in an encrypted
        database column, NOT in the cache file.
        
        Process:
        1. Compute SHA-256 hash
        2. Check cache for existing parse (returns scrubbed_text only)
        3. If not cached, parse with LlamaParse
        4. **Extract structured fields BEFORE scrubbing** (if extractor provided)
        5. Apply privacy scrubbing
        6. Cache the scrubbed result (extracted_fields NOT cached - store separately)
        
        Args:
            file_path: Path to the PDF file.
            field_extractor: Optional callback to extract structured fields from raw text.
                           This runs BEFORE scrubbing so it sees real values.
            
        Returns:
            ParsedDocument with scrubbed_text and extracted_fields (in memory).
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Step 1: Compute hash
        content_hash = self.compute_file_hash(file_path)
        
        # Step 2: Check cache
        cached = self.load_from_cache(content_hash)
        if cached:
            # NOTE: cached version only has scrubbed_text, not extracted_fields
            # If caller needs extracted_fields, they must re-parse or load from DB
            return cached
        
        # Step 3: Parse document (raw text with PII)
        raw_text = self.parse_with_llamaparse(file_path)
        
        # Step 4: EXTRACT FIELDS BEFORE SCRUBBING (critical for form filling)
        extracted_fields = {}
        if field_extractor:
            extracted_fields = field_extractor(raw_text)
            # NOTE: Caller is responsible for storing extracted_fields securely
            # (e.g., encrypted column in Postgres)
        
        # Step 5: Apply privacy scrubbing
        scrubbed_text = self.privacy_pipeline.scrub(raw_text)
        
        # Step 6: Create document record
        doc = ParsedDocument(
            document_id=content_hash[:16],
            original_filename=file_path.name,
            content_hash=content_hash,
            raw_text=raw_text,  # In-memory only, not persisted
            scrubbed_text=scrubbed_text,
            extracted_fields=extracted_fields,  # In-memory only, not persisted
            metadata={
                "file_size_bytes": file_path.stat().st_size,
                "parse_method": "llamaparse",
            }
        )
        
        # Step 7: Cache (only scrubbed_text and metadata - NO PII)
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


if __name__ == "__main__":

    import sys
from pathlib import Path

# Add project root to path for imports (allows running this file directly)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

    # Test the ingestion service with a sample offer letter
    from app.core.config import DATA_DIR
    
    ingestion_service = get_ingestion_service()
    
    # Use absolute path
    test_file = DATA_DIR / "templates" / "OPT_offer_letter_sample.pdf"
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        print(f"   Create a sample offer letter PDF at this location to test.")
    else:
        print(f"📄 Testing ingestion on: {test_file.name}")
        doc = ingestion_service.ingest_pdf(test_file)
        
        print(f"\n✅ Successfully ingested!")
        print(f"   Document ID: {doc.document_id}")
        print(f"   Content Hash: {doc.content_hash[:16]}...")
        print(f"   Scrubbed Text Length: {len(doc.scrubbed_text)} chars")
        print(f"\n   First 200 chars of scrubbed text:")
        print(f"   {doc.scrubbed_text[:200]}...")


if __name__ == "__main__":
    ingestion_service = get_ingestion_service()
    doc = ingestion_service.ingest_pdf("data/templates/OPT_offer_letter_sample.pdf")
    print(doc)
