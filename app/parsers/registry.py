"""
Parser Registry

Factory for getting the appropriate parser based on document type.
"""

from typing import Optional

from app.parsers.base import BaseParser, DocumentType
from app.parsers.i20_parser import I20Parser
from app.parsers.offer_letter_parser import OfferLetterParser


# Registry mapping document types to parser classes
_PARSER_REGISTRY = {
    DocumentType.I20: I20Parser,
    DocumentType.OFFER_LETTER: OfferLetterParser,
    # Add more parsers as implemented
    # DocumentType.I983: I983Parser,
    # DocumentType.EAD_CARD: EADCardParser,
}


class GenericParser(BaseParser):
    """Fallback parser for unknown document types."""
    
    document_type = DocumentType.GENERIC
    
    def pre_redact(self, raw_text: str) -> str:
        """No document-specific redaction for generic documents."""
        return raw_text
    
    def extract_fields(self, text: str) -> dict:
        """No structured extraction for generic documents."""
        return {
            "note": "Generic document - no structured extraction available"
        }


def get_parser(document_type: DocumentType) -> BaseParser:
    """
    Get the appropriate parser for a document type.
    
    Args:
        document_type: The type of document to parse
        
    Returns:
        An instance of the appropriate parser
        
    Example:
        >>> parser = get_parser(DocumentType.I20)
        >>> result = parser.parse(raw_text)
    """
    parser_class = _PARSER_REGISTRY.get(document_type, GenericParser)
    return parser_class()


def get_supported_types() -> list[DocumentType]:
    """Get list of document types that have specialized parsers."""
    return list(_PARSER_REGISTRY.keys())
