"""
I-20 Document Parser

Specialized parser for Form I-20 (Certificate of Eligibility for Nonimmigrant Student Status).

Key features:
- Pre-redacts names in structured fields (fixes "NAME: Sanjeeb Subedi" issue)
- Extracts SEVIS ID, program dates, school information
- Validates required I-20 fields
"""

import re
from typing import Dict, Any
from datetime import datetime

from app.parsers.base import BaseParser, DocumentType


class I20Parser(BaseParser):
    """Parser for Form I-20 documents."""
    
    document_type = DocumentType.I20
    
    def pre_redact(self, raw_text: str) -> str:
        """
        Apply I-20 specific redaction rules.
        
        Critical fixes:
        1. "NAME: <student name>" patterns (main issue)
        2. "STUDENT NAME:" patterns
        3. Names in signature blocks
        4. Parent/Guardian names
        """
        text = raw_text
        
        # Pattern 1: Header section - "NAME: Sanjeeb Subedi"
        # This is the CRITICAL fix for the privacy leak
        text = re.sub(
            r'(NAME:)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'\1 [PERSON_NAME]',
            text,
            flags=re.MULTILINE
        )
        
        # Pattern 2: "STUDENT NAME:" variations
        text = re.sub(
            r'(STUDENT NAME:)\s*([^\n]+)',
            r'\1 [PERSON_NAME]',
            text,
            flags=re.IGNORECASE
        )
        
        # Pattern 3: Signature blocks - "SIGNATURE OF: <name>"
        text = re.sub(
            r'(SIGNATURE OF:)\s*([^\n]+)',
            r'\1 [PERSON_NAME]',
            text,
            flags=re.IGNORECASE
        )
        
        # Pattern 4: Parent/Guardian names in structured fields
        text = re.sub(
            r'(NAME OF PARENT OR GUARDIAN)\s*([^\n]+)',
            r'\1 [PERSON_NAME]',
            text,
            flags=re.IGNORECASE
        )
        
        # Pattern 5: School official names (DSO, etc.)
        text = re.sub(
            r'(Designated School Official:?)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'\1 [PERSON_NAME]',
            text,
            flags=re.IGNORECASE
        )
        
        # Pattern 6: Table rows with student name (CRITICAL!)
        # I-20 has a table like:
        # | **SURNAME/PRIMARY NAME** | **GIVEN NAME** | **Class of Admission** |
        # | ------------------------ | -------------- | ---------------------- |
        # | Subedi                   | Sanjeeb        | F-1                    |
        #
        # We need to redact the name cells in the data row
        text = re.sub(
            r'(\| \*\*SURNAME/PRIMARY NAME\*\*.*\n\|.*\n)\|\s*(\w+)\s*\|\s*(\w+)\s*\|(.+)',
            r'\1| [SURNAME] | [GIVEN_NAME] |\4',
            text,
            flags=re.IGNORECASE
        )
        
        return text
    
    def extract_fields(self, text: str) -> Dict[str, Any]:
        """
        Extract structured fields from I-20.
        
        Fields extracted:
        - SEVIS ID
        - School name
        - Program dates (start, end)
        - Degree level
        - Major/Field of study
        - Date of birth (if present)
        """
        fields = {}
        
        # SEVIS ID (already redacted, but extract placeholder location)
        sevis_match = re.search(r'SEVIS ID:\s*(\[SEVIS_ID\]|N\d{10})', text)
        if sevis_match:
            fields['sevis_id_detected'] = True
            fields['sevis_id_placeholder'] = sevis_match.group(1)
        
        # School name - usually appears near the top
        # Look for "School name" or similar labels
        school_match = re.search(
            r'(?:SCHOOL NAME|School:|Institution)(?:\s*:)?\s*([^\n]+)',
            text,
            flags=re.IGNORECASE
        )
        if school_match:
            fields['school_name'] = school_match.group(1).strip()
        
        # Program start date
        start_date_match = re.search(
            r'(?:PROGRAM START DATE|Program begins)(?:\s*:)?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            text,
            flags=re.IGNORECASE
        )
        if start_date_match:
            fields['program_start_date'] = start_date_match.group(1)
        
        # Program end date
        end_date_match = re.search(
            r'(?:PROGRAM END DATE|Program ends)(?:\s*:)?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            text,
            flags=re.IGNORECASE
        )
        if end_date_match:
            fields['program_end_date'] = end_date_match.group(1)
        
        # Level of education
        level_match = re.search(
            r'(?:EDUCATION LEVEL|Degree level|Program of study)(?:\s*:)?\s*([^\n]+)',
            text,
            flags=re.IGNORECASE
        )
        if level_match:
            level = level_match.group(1).strip()
            # Normalize common values
            if any(term in level.lower() for term in ['bachelor', 'undergraduate', 'b.s.', 'b.a.']):
                fields['education_level'] = 'Bachelor'
            elif any(term in level.lower() for term in ['master', 'graduate', 'm.s.', 'm.a.']):
                fields['education_level'] = 'Master'
            elif any(term in level.lower() for term in ['doctor', 'phd', 'ph.d.']):
                fields['education_level'] = 'Doctoral'
            else:
                fields['education_level'] = level
        
        # Major/Field of study
        major_match = re.search(
            r'(?:MAJOR|Field of study|Major area)(?:\s*:)?\s*([^\n]+)',
            text,
            flags=re.IGNORECASE
        )
        if major_match:
            fields['major'] = major_match.group(1).strip()
        
        # Detect if this is STEM (for OPT eligibility)
        if 'major' in fields:
            stem_keywords = [
                'computer', 'engineering', 'science', 'mathematics', 
                'technology', 'physics', 'chemistry', 'biology'
            ]
            is_stem = any(kw in fields['major'].lower() for kw in stem_keywords)
            fields['is_stem'] = is_stem
        
        return fields
    
    def validate_fields(self, fields: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate that critical I-20 fields were extracted.
        
        Required fields:
        - SEVIS ID detected
        - Program dates
        """
        errors = []
        
        if not fields.get('sevis_id_detected'):
            errors.append("SEVIS ID not found in document")
        
        if not fields.get('program_start_date'):
            errors.append("Program start date not found")
        
        if not fields.get('program_end_date'):
            errors.append("Program end date not found")
        
        if not fields.get('school_name'):
            errors.append("School name not found")
        
        is_valid = len(errors) == 0
        return is_valid, errors
