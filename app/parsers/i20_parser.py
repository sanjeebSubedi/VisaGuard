"""
I-20 Parser - Specialized parser for Form I-20 (Certificate of Eligibility)

The I-20 has a very specific structure with labeled fields.
This parser uses strict regex to:
1. Redact PII that appears in known locations (NAME:, etc.)
2. Extract key fields like SEVIS ID, program dates, school info
"""

import re
from datetime import datetime
from typing import Optional

from app.parsers.base import BaseParser, DocumentType, ParsedDocument
from app.parsers.registry import ParserRegistry


@ParserRegistry.register(DocumentType.I20)
class I20Parser(BaseParser):
    """
    Parser for Form I-20 (Certificate of Eligibility for Nonimmigrant Student Status).
    
    Known PII locations in I-20:
    - NAME: <student name>
    - SIGNATURE OF: <name>
    - NAME OF PARENT OR GUARDIAN
    - Student address fields
    """
    
    doc_type = DocumentType.I20
    
    # Regex patterns for I-20 specific PII locations
    # These are strict patterns based on the known I-20 form layout
    PII_PATTERNS = [
        # NAME: followed by text until newline or specific delimiter
        (r"(NAME:\s*)([A-Za-z][A-Za-z\s\-\.,']+?)(?=\n|\s{2,}|$)", r"\1[PERSON_NAME]"),
        # SEVIS ID with name on same line: "SEVIS ID: N... (F-1) NAME: John Smith"
        (r"(NAME:\s*)([A-Za-z][A-Za-z\s\-\.,']+)", r"\1[PERSON_NAME]"),
        # SIGNATURE OF: <name>
        (r"(SIGNATURE OF:\s*)([A-Za-z][A-Za-z\s\-\.,']+?)(?=\s*DATE)", r"\1[PERSON_NAME]"),
        # Standalone full names after specific headers
        (r"(Student Name[:\s]+)([A-Z][a-z]+\s+[A-Z][a-z]+)", r"\1[PERSON_NAME]"),
        # Parent/guardian
        (r"(PARENT OR GUARDIAN\s*)([A-Za-z][A-Za-z\s\-\.,']+?)(?=\s*SIGNATURE)", r"\1[PERSON_NAME]"),
        # Birth date (MM/DD/YYYY or similar)
        (r"(DATE OF BIRTH[:\s]*)(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", r"\1[DOB]"),
        # Country of birth
        (r"(COUNTRY OF BIRTH[:\s]*)([A-Za-z\s]+?)(?=\n|\s{2,}|$)", r"\1[COUNTRY]"),
        # Student address - redact full address blocks
        (r"(ADDRESS[:\s]*)(\d+[^,\n]+,\s*[^,\n]+,\s*[A-Z]{2}\s*\d{5})", r"\1[ADDRESS]"),
    ]
    
    # Field extraction patterns
    FIELD_PATTERNS = {
        "sevis_id": r"SEVIS ID[:\s]*([NM]\d{10})",
        "school_name": r"SCHOOL NAME[:\s]*([^\n]+)",
        "school_code": r"SCHOOL CODE[:\s]*([A-Z]{3}\d{3}[A-Z]\d{5})",
        "program_start_date": r"PROGRAM START DATE[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        "program_end_date": r"PROGRAM END DATE[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        "level_of_education": r"LEVEL OF EDUCATION[:\s]*([^\n]+)",
        "major": r"MAJOR[:\s]*([^\n]+)",
        "cip_code": r"CIP CODE[:\s]*(\d{2}\.\d{4})",
    }
    
    def pre_redact(self, text: str) -> str:
        """
        Apply I-20 specific PII redaction.
        
        These patterns target exact locations in the I-20 form
        where PII appears, fixing the issue where "NAME: John Smith"
        wasn't being caught by generic NER.
        """
        result = text
        
        for pattern, replacement in self.PII_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE | re.MULTILINE)
        
        return result
    
    def extract_fields(self, text: str) -> dict:
        """
        Extract structured fields from I-20.
        
        Returns dict with SEVIS ID, program dates, school info, etc.
        """
        fields = {}
        
        for field_name, pattern in self.FIELD_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields[field_name] = match.group(1).strip()
        
        return fields
    
    def post_process(self, doc: ParsedDocument) -> ParsedDocument:
        """Validate extracted fields and add warnings."""
        # Warn if SEVIS ID not found (critical field)
        if not doc.extracted_fields.get("sevis_id"):
            doc.warnings.append("SEVIS ID not found - may need manual entry")
        
        # Warn if program end date is in the past
        end_date_str = doc.extracted_fields.get("program_end_date")
        if end_date_str:
            try:
                # Try common date formats
                for fmt in ["%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d"]:
                    try:
                        end_date = datetime.strptime(end_date_str, fmt).date()
                        if end_date < datetime.now().date():
                            doc.warnings.append(f"Program end date ({end_date_str}) is in the past")
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
        
        return doc
