"""
Base Parser Interface

Defines the contract that all document-specific parsers must follow.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass


class DocumentType(str, Enum):
    """Supported document types for specialized parsing."""
    I20 = "i20"
    OFFER_LETTER = "offer_letter"
    I983 = "i983"
    EAD_CARD = "ead_card"
    GENERIC = "generic"


@dataclass
class ParsedDocument:
    """Result of document parsing."""
    document_type: DocumentType
    extracted_fields: Dict[str, Any]
    preprocessed_text: str  # Text after pre-redaction but before generic scrubbing
    metadata: Dict[str, Any]


class BaseParser(ABC):
    """
    Base class for document-specific parsers.
    
    Each parser handles:
    1. Pre-redaction: Document-specific privacy rules (e.g., regex for form headers)
    2. Field extraction: Pull structured data from known locations
    3. Validation: Ensure required fields are present
    
    The general flow:
    - ingest_pdf() extracts raw text
    - pre_redact() applies document-specific privacy rules
    - generic privacy pipeline scrubs remaining PII
    - extract_fields() pulls structured data
    """
    
    document_type: DocumentType
    
    @abstractmethod
    def pre_redact(self, raw_text: str) -> str:
        """
        Apply document-specific privacy rules BEFORE generic scrubbing.
        
        Use this for:
        - Form headers where names appear in fixed positions
        - Structured fields that generic NER misses
        - Document-specific patterns
        
        Args:
            raw_text: The original text from PDF parsing
            
        Returns:
            Text with document-specific PII redacted
        """
        pass
    
    @abstractmethod
    def extract_fields(self, text: str) -> Dict[str, Any]:
        """
        Extract structured fields from the document.
        
        This runs AFTER both pre-redaction and generic scrubbing.
        Extract metadata and document structure, not PII.
        
        Args:
            text: The fully scrubbed text
            
        Returns:
            Dictionary of extracted fields
        """
        pass
    
    def validate_fields(self, fields: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate that required fields were extracted.
        
        Args:
            fields: The extracted fields dictionary
            
        Returns:
            Tuple of (is_valid, list of missing/invalid fields)
        """
        # Default implementation - subclasses can override
        return True, []
    
    def parse(self, raw_text: str) -> ParsedDocument:
        """
        Full parsing pipeline for this document type.
        
        Args:
            raw_text: The original PDF text
            
        Returns:
            ParsedDocument with all extracted information
        """
        # Step 1: Pre-redaction
        preprocessed = self.pre_redact(raw_text)
        
        # Step 2: Extract fields (note: generic scrubbing happens in ingestion service)
        # For now, extract from preprocessed text
        # TODO: After integration, this will receive fully scrubbed text
        fields = self.extract_fields(preprocessed)
        
        # Step 3: Validate
        is_valid, errors = self.validate_fields(fields)
        
        return ParsedDocument(
            document_type=self.document_type,
            extracted_fields=fields,
            preprocessed_text=preprocessed,
            metadata={
                "validation_passed": is_valid,
                "validation_errors": errors,
            }
        )
