"""
Parser Registry - Factory for getting the right parser for each document type
"""

from typing import Optional

from app.parsers.base import BaseParser, DocumentType


class ParserRegistry:
    """
    Registry of document parsers.
    
    Usage:
        registry = ParserRegistry()
        parser = registry.get(DocumentType.I20)
        result = parser.parse(text)
    """
    
    _parsers: dict[DocumentType, type[BaseParser]] = {}
    
    @classmethod
    def register(cls, doc_type: DocumentType):
        """Decorator to register a parser class."""
        def decorator(parser_class: type[BaseParser]):
            cls._parsers[doc_type] = parser_class
            return parser_class
        return decorator
    
    @classmethod
    def get(cls, doc_type: DocumentType) -> BaseParser:
        """
        Get a parser instance for the given document type.
        
        Args:
            doc_type: The type of document to parse
            
        Returns:
            An instance of the appropriate parser
            
        Raises:
            ValueError: If no parser is registered for this type
        """
        parser_class = cls._parsers.get(doc_type)
        if parser_class is None:
            # Fall back to generic parser
            from app.parsers.generic import GenericParser
            return GenericParser()
        return parser_class()
    
    @classmethod
    def list_supported(cls) -> list[DocumentType]:
        """List all document types with registered parsers."""
        return list(cls._parsers.keys())


def get_parser(doc_type: DocumentType) -> BaseParser:
    """Convenience function to get a parser."""
    return ParserRegistry.get(doc_type)
