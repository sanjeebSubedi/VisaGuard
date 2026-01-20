"""
Offer Letter Parser - Specialized parser for employment offer letters

Offer letters contain critical employment information for OPT:
- Employer name, EIN, address
- Job title, start date, hours per week
- Compensation details
"""

import re
from datetime import datetime
from typing import Optional

from app.parsers.base import BaseParser, DocumentType, ParsedDocument
from app.parsers.registry import ParserRegistry


@ParserRegistry.register(DocumentType.OFFER_LETTER)
class OfferLetterParser(BaseParser):
    """
    Parser for employment offer letters.
    
    Extracts employer and position details needed for OPT compliance.
    """
    
    doc_type = DocumentType.OFFER_LETTER
    
    # PII patterns specific to offer letters
    PII_PATTERNS = [
        # "Mr./Ms./Mrs. John Smith"
        (r"(Mr\.|Ms\.|Mrs\.|Dr\.)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)", r"\1 [PERSON_NAME]"),
        # "Dear John Smith" or "Dear Mr. Smith"
        (r"(Dear\s+)(Mr\.|Ms\.|Mrs\.|Dr\.)?\s*([A-Z][a-z]+(\s+[A-Z][a-z]+)?)", r"\1[PERSON_NAME]"),
        # Supervisor/Manager names after titles
        (r"(supervised by[:\s]+)([A-Z][a-z]+\s+[A-Z][a-z]+)", r"\1[PERSON_NAME]"),
        (r"(Manager[:\s]+)([A-Z][a-z]+\s+[A-Z][a-z]+)", r"\1[PERSON_NAME]"),
        (r"(Supervisor[:\s]+)([A-Z][a-z]+\s+[A-Z][a-z]+)", r"\1[PERSON_NAME]"),
        # Signatory names
        (r"(Sincerely,?\s*\n+)([A-Z][a-z]+\s+[A-Z][a-z]+)", r"\1[PERSON_NAME]"),
    ]
    
    # Field extraction patterns
    FIELD_PATTERNS = {
        "company_name": [
            r"^([A-Z][A-Za-z\s&,\.]+(?:LLC|Inc|Corp|Company|Ltd))\s*$",
            r"([\w\s]+(?:LLC|Inc|Corp|Company|Ltd))",
        ],
        "ein": r"(?:EIN|Employer Identification Number)[:\s]*(\d{2}[‐\-]\d{7})",
        "position_title": [
            r"(?:Position|Title|Role)[:\s]*([^\n]+)",
            r"position (?:of|as)\s+([^\n\.]+)",
        ],
        "start_date": [
            r"(?:Start Date|Starting|Effective)[:\s]*(\w+\s+\d{1,2},?\s*\d{4}|\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        ],
        "hours_per_week": r"(\d{1,2})\s*hours?\s*(?:per|/)\s*week",
        "compensation": [
            r"\$\s*([\d,]+(?:\.\d{2})?)\s*(?:per|/)\s*(?:hour|yr|year|annually)",
            r"(?:Salary|Compensation|Pay)[:\s]*\$\s*([\d,]+(?:\.\d{2})?)",
        ],
        "work_location": r"(?:Work Location|Office|Located at)[:\s]*([^\n]+)",
    }
    
    def pre_redact(self, text: str) -> str:
        """Apply offer letter specific PII redaction."""
        result = text
        
        for pattern, replacement in self.PII_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE | re.MULTILINE)
        
        return result
    
    def extract_fields(self, text: str) -> dict:
        """
        Extract employment details from offer letter.
        
        Returns dict with company, position, dates, compensation, etc.
        """
        fields = {}
        
        for field_name, patterns in self.FIELD_PATTERNS.items():
            # Handle single pattern or list of patterns
            if isinstance(patterns, str):
                patterns = [patterns]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    fields[field_name] = match.group(1).strip()
                    break
        
        return fields
    
    def post_process(self, doc: ParsedDocument) -> ParsedDocument:
        """Validate employment details."""
        
        # Warn if hours < 20 (minimum for STEM OPT)
        hours = doc.extracted_fields.get("hours_per_week")
        if hours:
            try:
                if int(hours) < 20:
                    doc.warnings.append(f"Hours per week ({hours}) is below STEM OPT minimum of 20")
            except ValueError:
                pass
        
        # Warn if no EIN found (required for STEM OPT)
        if not doc.extracted_fields.get("ein"):
            doc.warnings.append("EIN not found - required for STEM OPT / I-983")
        
        return doc
