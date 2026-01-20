"""
Document Parsers Module

Provides specialized parsing and PII redaction for each supported document type.
Each parser knows the exact structure of its document, enabling:
- Precise field extraction
- Targeted PII redaction (no false positives)
- Structured data output
"""

from app.parsers.base import BaseParser, DocumentType, ParsedDocument
from app.parsers.registry import ParserRegistry, get_parser

# Import specialized parsers to trigger registration
from app.parsers.generic import GenericParser
from app.parsers.i20_parser import I20Parser
from app.parsers.offer_letter_parser import OfferLetterParser

__all__ = [
    "BaseParser",
    "DocumentType",
    "ParsedDocument",
    "ParserRegistry",
    "get_parser",
    "GenericParser",
    "I20Parser",
    "OfferLetterParser",
]
