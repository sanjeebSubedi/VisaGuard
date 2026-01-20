"""
Offer Letter Parser

Specialized parser for employment offer letters.

Key features:
- Extracts employer information (company name, EIN, address)
- Job details (title, start date, compensation)
- OPT compliance statements
"""

import re
from typing import Dict, Any

from app.parsers.base import BaseParser, DocumentType


class OfferLetterParser(BaseParser):
    """Parser for employment offer letters."""
    
    document_type = DocumentType.OFFER_LETTER
    
    def pre_redact(self, raw_text: str) -> str:
        """
        Apply offer letter specific redaction.
        
        Offer letters have less structure than I-20, so we rely more
        on the generic privacy pipeline. Only handle special cases here.
        """
        text = raw_text
        
        # Pattern: "Dear <Name>," at the start of letters
        text = re.sub(
            r'(Dear)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)(,)',
            r'\1 [PERSON_NAME]\3',
            text
        )
        
        # Pattern: Letter signatures - "Sincerely, <Name>"
        text = re.sub(
            r'(Sincerely,?)\s*\n+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'\1\n[PERSON_NAME]',
            text,
            flags=re.MULTILINE
        )
        
        return text
    
    def extract_fields(self, text: str) -> Dict[str, Any]:
        """
        Extract structured fields from offer letter.
        
        Fields extracted:
        - Company name
        - EIN (Employer Identification Number)
        - Job title
        - Start date
        - Compensation
        - Hours per week
        - Work location
        """
        fields = {}
        
        # Company name (usually in letterhead or first paragraph)
        # Look for company patterns
        company_match = re.search(
            r'(?:^|\n)([A-Z][A-Za-z\s&,\.]+(?:LLC|Inc|Corp|Corporation|Ltd|Company))',
            text
        )
        if company_match:
            fields['company_name'] = company_match.group(1).strip()
        
        # EIN - Format: 12-3456789
        ein_match = re.search(r'EIN[:\s]+(\d{2}-\d{7})', text, flags=re.IGNORECASE)
        if ein_match:
            fields['ein'] = ein_match.group(1)
        
        # Job title
        title_match = re.search(
            r'(?:Position|Title|Role)(?:\s*:)?\s*([^\n]+)',
            text,
            flags=re.IGNORECASE
        )
        if title_match:
            fields['job_title'] = title_match.group(1).strip()
        
        # Start date
        start_match = re.search(
            r'(?:Start Date|Begin|Commence)(?:\s*:)?\s*(\w+\s+\d{1,2},?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            text,
            flags=re.IGNORECASE
        )
        if start_match:
            fields['start_date'] = start_match.group(1).strip()
        
        # End date (if contract position)
        end_match = re.search(
            r'(?:End Date|Terminate|Conclude)(?:\s*:)?\s*(\w+\s+\d{1,2},?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            text,
            flags=re.IGNORECASE
        )
        if end_match:
            fields['end_date'] = end_match.group(1).strip()
        
        # Compensation - hourly or salary
        compensation_match = re.search(
            r'(?:Salary|Compensation|Pay)(?:\s*:)?\s*\$?([\d,]+(?:\.\d{2})?)\s*(?:per hour|/hour|hourly|annually|/year)?',
            text,
            flags=re.IGNORECASE
        )
        if compensation_match:
            fields['compensation'] = compensation_match.group(1)
            # Detect if hourly or annual
            if 'hour' in compensation_match.group(0).lower():
                fields['compensation_type'] = 'hourly'
            elif 'annual' in compensation_match.group(0).lower() or 'year' in compensation_match.group(0).lower():
                fields['compensation_type'] = 'annual'
        
        # Hours per week
        hours_match = re.search(
            r'(\d+)\s*hours?\s*(?:per week|/week|weekly)',
            text,
            flags=re.IGNORECASE
        )
        if hours_match:
            fields['hours_per_week'] = int(hours_match.group(1))
        
        # Work location (city, state)
        location_match = re.search(
            r'(?:Location|Work site|Office)(?:\s*:)?\s*([^\n]+)',
            text,
            flags=re.IGNORECASE
        )
        if location_match:
            fields['work_location'] = location_match.group(1).strip()
        
        # Check for OPT compliance statement
        opt_compliance = bool(re.search(
            r'(?:OPT|Optional Practical Training|F-1)',
            text,
            flags=re.IGNORECASE
        ))
        fields['mentions_opt'] = opt_compliance
        
        return fields
    
    def validate_fields(self, fields: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate that critical offer letter fields were extracted.
        
        Required fields:
        - Company name
        - Job title
        - Start date
        """
        errors = []
        
        if not fields.get('company_name'):
            errors.append("Company name not found")
        
        if not fields.get('job_title'):
            errors.append("Job title not found")
        
        if not fields.get('start_date'):
            errors.append("Start date not found")
        
        if not fields.get('ein'):
            errors.append("EIN not found (required for STEM OPT)")
        
        is_valid = len(errors) == 0
        return is_valid, errors
