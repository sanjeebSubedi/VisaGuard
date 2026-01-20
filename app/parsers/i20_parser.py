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
        Extract structured fields from I-20 with robust pattern matching.
        
        Fields extracted:
        - SEVIS ID
        - School name
        - Program dates (start, end)
        - Degree level
        - Major/Field of study
        
        Uses multiple fallback patterns to handle I-20 format variations.
        """
        fields = {}
        
        # === SEVIS ID (CRITICAL) ===
        # Try multiple patterns with increasing flexibility
        sevis_patterns = [
            r'SEVIS\s*ID\s*:\s*(\[SEVIS_ID\]|N\d{10})',  # Standard with colon
            r'SEVIS\s*ID\s*(\[SEVIS_ID\]|N\d{10})',       # Without colon
            r'SEVIS\s*#?\s*(\[SEVIS_ID\]|N\d{10})',       # With # symbol
            r'\[SEVIS_ID\]',                               # Just the placeholder
            r'N\d{10}',                                    # Raw SEVIS number
        ]
        
        for pattern in sevis_patterns:
            sevis_match = re.search(pattern, text, re.IGNORECASE)
            if sevis_match:
                fields['sevis_id_detected'] = True
                if sevis_match.groups():
                    fields['sevis_id_placeholder'] = sevis_match.group(1)
                else:
                    fields['sevis_id_placeholder'] = sevis_match.group(0)
                break
        
        # === SCHOOL NAME ===
        # Try multiple patterns and filter out junk
        school_patterns = [
            r'(?:SCHOOL\s+NAME|Institution\s+Name)\s*:?\s*([^\n\|]+?)(?:\n|\|)',
            r'School:\s*([^\n\|]+)',
            r'(?:Name\s+of\s+School|School)\s*:?\s*([A-Z][^\n\|]{10,80})',  # At least 10 chars, max 80
        ]
        
        for pattern in school_patterns:
            school_match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if school_match:
                school_name = school_match.group(1).strip()
                # Filter out markdown table syntax
                if '**' not in school_name and '|' not in school_name and len(school_name) > 5:
                    fields['school_name'] = school_name
                    break
        
        # === PROGRAM DATES ===
        # Support multiple date formats: MM/DD/YYYY, MM-DD-YYYY, Month DD, YYYY
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # 01/15/2024 or 01-15-24
            r'[A-Z][a-z]+\s+\d{1,2},?\s+\d{4}',  # January 15, 2024
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',     # 2024/01/15
        ]
        
        # Program start date
        start_labels = [
            r'PROGRAM\s+START\s+DATE',
            r'Program\s+begins',
            r'Start\s+Date',
            r'Admission\s+Date',
        ]
        
        for label in start_labels:
            for date_pattern in date_patterns:
                full_pattern = f'{label}\\s*:?\\s*({date_pattern})'
                start_match = re.search(full_pattern, text, re.IGNORECASE)
                if start_match:
                    fields['program_start_date'] = start_match.group(1).strip()
                    break
            if 'program_start_date' in fields:
                break
        
        # Program end date
        end_labels = [
            r'PROGRAM\s+END\s+DATE',
            r'Program\s+ends?',
            r'End\s+Date',
            r'Expected\s+Completion',
        ]
        
        for label in end_labels:
            for date_pattern in date_patterns:
                full_pattern = f'{label}\\s*:?\\s*({date_pattern})'
                end_match = re.search(full_pattern, text, re.IGNORECASE)
                if end_match:
                    fields['program_end_date'] = end_match.group(1).strip()
                    break
            if 'program_end_date' in fields:
                break
        
        # === EDUCATION LEVEL ===
        level_patterns = [
            r'(?:EDUCATION\s+LEVEL|Degree\s+level|Level\s+of\s+Education)\s*:?\s*([^\n\|]+?)(?:\n|\|)',
            r'(?:Bachelor|Master|Doctor|Associate|PhD|Ph\.?D\.?)',
        ]
        
        for pattern in level_patterns:
            level_match = re.search(pattern, text, re.IGNORECASE)
            if level_match:
                level_text = level_match.group(1) if level_match.groups() else level_match.group(0)
                level = level_text.strip()
                
                # Filter out markdown
                if '**' in level or '|' in level:
                    continue
                
                # Normalize common values
                level_lower = level.lower()
                if any(term in level_lower for term in ['bachelor', 'undergraduate', 'b.s.', 'b.a.']):
                    fields['education_level'] = 'Bachelor'
                elif any(term in level_lower for term in ['master', 'graduate', 'm.s.', 'm.a.']):
                    fields['education_level'] = 'Master'
                elif any(term in level_lower for term in ['doctor', 'phd', 'ph.d.', 'doctoral']):
                    fields['education_level'] = 'Doctoral'
                elif any(term in level_lower for term in ['associate', 'a.a.', 'a.s.']):
                    fields['education_level'] = 'Associate'
                else:
                    fields['education_level'] = level
                break
        
        # === MAJOR / FIELD OF STUDY ===
        major_patterns = [
            r'(?:MAJOR|Field\s+of\s+study|Major\s+area|Program\s+of\s+study)\s*:?\s*([^\n\|]{5,100}?)(?:\n|\|)',
            r'Major\s*1?\s*:?\s*([A-Z][^\n\|]{5,80})',
        ]
        
        for pattern in major_patterns:
            major_match = re.search(pattern, text, re.IGNORECASE)
            if major_match:
                major = major_match.group(1).strip()
                # Filter out markdown and junk
                if '**' not in major and major.count('|') < 2 and len(major) > 3:
                    fields['major'] = major
                    break
        
        # Detect if this is STEM (for OPT eligibility)
        if 'major' in fields:
            stem_keywords = [
                'computer', 'engineering', 'science', 'mathematics', 
                'technology', 'physics', 'chemistry', 'biology',
                'software', 'data', 'electrical', 'mechanical'
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
