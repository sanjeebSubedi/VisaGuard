"""
Generic Parser - Fallback for unknown document types

Uses only the generic Presidio pipeline without form-specific logic.
"""

from app.parsers.base import BaseParser, DocumentType


class GenericParser(BaseParser):
    """
    Fallback parser for documents without a specialized parser.
    
    Does minimal form-specific processing - relies entirely on
    the generic Presidio privacy pipeline.
    """
    
    doc_type = DocumentType.OTHER
    
    def pre_redact(self, text: str) -> str:
        """No form-specific redaction for generic documents."""
        return text
    
    def extract_fields(self, text: str) -> dict:
        """No field extraction for generic documents."""
        return {}
