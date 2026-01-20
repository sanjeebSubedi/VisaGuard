"""
Base Parser - Abstract interface for document-type-specific parsers

Each specialized parser inherits from BaseParser and provides:
1. pre_redact(): Form-aware PII scrubbing BEFORE generic Presidio
2. extract_fields(): Structured field extraction from the document
3. post_process(): Any cleanup or validation after parsing
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class DocumentType(str, Enum):
    """Supported document types for F-1 OPT compliance."""
    I20 = "i20"
    OFFER_LETTER = "offer_letter"
    I983 = "i983"
    EAD_CARD = "ead_card"
    PAY_STUB = "pay_stub"
    OTHER = "other"


@dataclass
class ParsedDocument:
    """Result of parsing a document with a specialized parser."""
    doc_type: DocumentType
    raw_text: str
    scrubbed_text: str
    extracted_fields: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    confidence: float = 1.0
    
    def get_field(self, key: str, default=None):
        """Safely get an extracted field."""
        return self.extracted_fields.get(key, default)


class BaseParser(ABC):
    """
    Abstract base for document-specific parsers.
    
    Each parser implements three phases:
    1. pre_redact: Apply form-specific regex to catch PII that generic NER misses
    2. extract_fields: Pull structured data from the document
    3. post_process: Validate and clean up the result
    """
    
    doc_type: DocumentType = DocumentType.OTHER
    
    @abstractmethod
    def pre_redact(self, text: str) -> str:
        """
        Apply document-specific PII redaction BEFORE generic Presidio.
        
        This is where we fix issues like "NAME: John Smith" not being caught.
        Use strict regex patterns based on known form layouts.
        
        Args:
            text: Raw parsed text from the document
            
        Returns:
            Text with form-specific PII redacted
        """
        pass
    
    @abstractmethod
    def extract_fields(self, text: str) -> dict:
        """
        Extract structured fields from the document.
        
        Args:
            text: Text (may be pre-redacted or raw depending on use)
            
        Returns:
            Dictionary of field names to values
        """
        pass
    
    def post_process(self, doc: ParsedDocument) -> ParsedDocument:
        """
        Optional post-processing hook.
        
        Override to add validation, date normalization, etc.
        Default implementation returns the document unchanged.
        """
        return doc
    
    def parse(self, raw_text: str, apply_generic_scrub: bool = True) -> ParsedDocument:
        """
        Full parsing pipeline.
        
        1. Extract fields from raw text (before redaction)
        2. Apply pre_redact (form-specific patterns)
        3. Optionally apply generic Presidio scrubbing
        4. Post-process
        
        Args:
            raw_text: The raw text parsed from the PDF
            apply_generic_scrub: Whether to also run Presidio after pre_redact
            
        Returns:
            ParsedDocument with extracted fields and scrubbed text
        """
        # 1. Extract fields FIRST (from raw text with PII)
        extracted = self.extract_fields(raw_text)
        
        # 2. Apply form-specific redaction
        scrubbed = self.pre_redact(raw_text)
        
        # 3. Optionally apply generic privacy pipeline
        if apply_generic_scrub:
            from app.privacy.pipeline import get_privacy_pipeline
            pipeline = get_privacy_pipeline()
            scrubbed = pipeline.scrub(scrubbed)
        
        # 4. Create result and post-process
        doc = ParsedDocument(
            doc_type=self.doc_type,
            raw_text=raw_text,
            scrubbed_text=scrubbed,
            extracted_fields=extracted,
        )
        
        return self.post_process(doc)
