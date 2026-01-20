"""
Test script for document parsers
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.parsers import DocumentType, get_parser
from app.core.config import DATA_DIR


def test_i20_parser():
    """Test I-20 parser with sample document."""
    print("=" * 60)
    print("Testing I-20 Parser")
    print("=" * 60)
    
    # Load raw I-20 text from LlamaParse result
    i20_path = DATA_DIR / "templates" / "i20_raw.txt"
    
    if not i20_path.exists():
        # Try the scrubbed version to show what we're working with
        i20_path = DATA_DIR / "templates" / "i20_scrubbed.txt"
        if not i20_path.exists():
            print(f"❌ No I-20 text file found at {i20_path}")
            return
    
    raw_text = i20_path.read_text()
    print(f"📄 Loaded {len(raw_text)} chars from {i20_path.name}")
    
    # Get the I-20 parser
    parser = get_parser(DocumentType.I20)
    print(f"🔧 Using parser: {type(parser).__name__}")
    
    # Parse (without generic scrub to test just our patterns)
    result = parser.parse(raw_text, apply_generic_scrub=False)
    
    print("\n📋 Extracted Fields:")
    for key, value in result.extracted_fields.items():
        print(f"   {key}: {value}")
    
    print("\n⚠️ Warnings:")
    for warning in result.warnings:
        print(f"   - {warning}")
    
    # Show redaction of the critical "NAME:" line
    print("\n🔍 Checking NAME redaction:")
    for line in result.scrubbed_text.split("\n"):
        if "NAME:" in line.upper():
            print(f"   {line}")
    
    return result


def test_offer_letter_parser():
    """Test Offer Letter parser."""
    print("\n" + "=" * 60)
    print("Testing Offer Letter Parser")
    print("=" * 60)
    
    offer_path = DATA_DIR / "templates" / "OPT_offer_letter_sample.pdf"
    
    # We need to parse the PDF first or use cached text
    # For now, let's use a sample text
    sample_text = """
    TechNova Systems LLC
    1234 Innovation Drive
    San Jose, CA 95134
    
    January 15, 2026
    
    Dear Mr. John Smith,
    
    We are pleased to offer you the position of Backend Software Engineer.
    
    Employment Details:
    - Position: Backend Software Engineer
    - Start Date: February 1, 2026
    - Hours per Week: 40 hours
    - Compensation: $38.50 per hour
    - EIN: 12-3456789
    
    You will be supervised by Jane Doe, Senior Engineering Manager.
    
    Sincerely,
    
    Michael Johnson
    Director of Engineering
    """
    
    parser = get_parser(DocumentType.OFFER_LETTER)
    print(f"🔧 Using parser: {type(parser).__name__}")
    
    result = parser.parse(sample_text, apply_generic_scrub=False)
    
    print("\n📋 Extracted Fields:")
    for key, value in result.extracted_fields.items():
        print(f"   {key}: {value}")
    
    print("\n⚠️ Warnings:")
    for warning in result.warnings:
        print(f"   - {warning}")
    
    print("\n🔍 Scrubbed text preview:")
    print(result.scrubbed_text[:500])
    
    return result


if __name__ == "__main__":
    test_i20_parser()
    test_offer_letter_parser()
