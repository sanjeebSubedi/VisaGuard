"""
Document Parser Module

Provides specialized parsers for different document types (I-20, Offer Letter, etc.)
with document-specific field extraction and privacy handling.
"""

from app.parsers.base import BaseParser, DocumentType
from app.parsers.i20_parser import I20Parser
from app.parsers.offer_letter_parser import OfferLetterParser
from app.parsers.registry import get_parser

__all__ = [
    "BaseParser",
    "DocumentType",
    "I20Parser",
    "OfferLetterParser",
    "get_parser",
]
