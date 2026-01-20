"""
Test I-20 Parser

Verifies that the I-20 parser correctly pre-redacts names and extracts fields.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import DATA_DIR
from app.parsers import get_parser, DocumentType
from app.services.ingestion import IngestionService

def test_i20_parser():
    """Test the I-20 parser on a real I-20 document."""
    
    # Load the I-20 PDF
    i20_path = DATA_DIR / "templates" / "i20.pdf"
    
    if not i20_path.exists():
        print(f"❌ I-20 PDF not found: {i20_path}")
        return
    
    print("Testing I-20 Parser")
    print("=" * 60)
    
    # Extract raw text from PDF
    print("\n📄 Extracting text from I-20 PDF...")
    ingestion = IngestionService()
    
    try:
        raw_text = ingestion.parse_with_llamaparse(i20_path)
        print(f"   Extracted {len(raw_text)} characters using LlamaParse")
    except Exception as e:
        print(f"   LlamaParse failed ({e}), trying pypdf...")
        import pypdf
        with open(i20_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            raw_text = '\n'.join(page.extract_text() for page in reader.pages)
        print(f"   Extracted {len(raw_text)} characters using pypdf")
    
    # Get the I-20 parser
    parser = get_parser(DocumentType.I20)
    
    # Step 1: Test pre-redaction
    print("\n🔒 Testing pre-redaction...")
    preprocessed = parser.pre_redact(raw_text)
    
    # Check if the critical issue is fixed
    if "Sanjeeb Subedi" in preprocessed:
        print("❌ FAILED: Name leak still present!")
        print(f"   Found: 'Sanjeeb Subedi' in preprocessed text")
        
        # Show context
        lines = preprocessed.split('\n')
        for i, line in enumerate(lines):
            if "Sanjeeb Subedi" in line:
                print(f"\n   Line {i}: {line}")
    elif "[PERSON_NAME]" in preprocessed:
        print("✅ PASSED: Name successfully redacted")
        
        # Show example
        name_lines = [line for line in preprocessed.split('\n') if '[PERSON_NAME]' in line]
        if name_lines:
            print(f"\n   Example redactions ({len(name_lines)} found):")
            for line in name_lines[:5]:
                print(f"   {line.strip()}")
    else:
        print("⚠️  WARNING: No [PERSON_NAME] placeholders found")
        print("   This might mean no names were detected (check raw text)")
    
    # Step 2: Extract fields
    print("\n📋 Extracting structured fields...")
    fields = parser.extract_fields(preprocessed)
    
    print(f"\n   Extracted {len(fields)} fields:")
    for key, value in fields.items():
        print(f"   - {key}: {value}")
    
    # Step 3: Validation
    print("\n✅ Validating extraction...")
    is_valid, errors = parser.validate_fields(fields)
    
    if is_valid:
        print("   ✓ All required fields extracted")
    else:
        print(f"   ✗ Validation failed:")
        for error in errors:
            print(f"     - {error}")
    
    # Step 4: Full parse test
    print("\n🔄 Testing full parse() method...")
    result = parser.parse(raw_text)
    
    print(f"\n   Document Type: {result.document_type}")
    print(f"   Validation Passed: {result.metadata['validation_passed']}")
    print(f"   Preprocessed Text Length: {len(result.preprocessed_text)} chars")
    
    return result


if __name__ == "__main__":
    test_i20_parser()
