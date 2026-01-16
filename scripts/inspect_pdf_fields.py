#!/usr/bin/env python3
"""
PDF Form Field Inspector (Value-Based Mapping)

Extracts filled form field values from a PDF where the user has manually
entered semantic labels into each field. Generates a mapping from
the user's semantic labels to the actual PDF field names.

Workflow:
1. User fills PDF with semantic labels (e.g., "STUDENT_FIRST_NAME" in the first name field)
2. Run this script on the filled PDF
3. Script generates mapping: {"STUDENT_FIRST_NAME": "Text_Field_01"}

Usage:
    uv run python scripts/inspect_pdf_fields.py data/templates/i983_labeled.pdf
"""

import json
import sys
from pathlib import Path

from pypdf import PdfReader


def extract_filled_fields(pdf_path: str) -> dict[str, dict]:
    """
    Extract all form fields that have non-empty values.
    
    Returns a dict mapping the user's semantic label (value) to field metadata.
    """
    reader = PdfReader(pdf_path)
    filled_fields = {}
    
    if reader.get_fields() is None:
        print(f"No AcroForm fields found in {pdf_path}")
        return filled_fields
    
    for field_name, field_obj in reader.get_fields().items():
        field_type = field_obj.get("/FT", "Unknown")
        field_value = field_obj.get("/V", "")
        
        # Convert to string and strip whitespace
        value_str = str(field_value).strip() if field_value else ""
        
        # Skip empty fields (these are likely section headers or unused)
        if not value_str:
            continue
        
        # Convert field type codes to readable names
        type_map = {
            "/Tx": "text",
            "/Btn": "checkbox",
            "/Ch": "dropdown",
            "/Sig": "signature",
        }
        readable_type = type_map.get(str(field_type), str(field_type))
        
        filled_fields[field_name] = {
            "semantic_label": value_str,
            "pdf_field_name": field_name,
            "type": readable_type,
        }
    
    return filled_fields


def generate_semantic_mapping(filled_fields: dict[str, dict]) -> dict[str, str]:
    """
    Generate a mapping from semantic labels to PDF field names.
    
    Returns: {"STUDENT_FIRST_NAME": "Text_Field_01", ...}
    """
    mapping = {}
    for field_name, props in filled_fields.items():
        semantic_label = props["semantic_label"]
        # Use the semantic label as the key, PDF field name as value
        mapping[semantic_label] = field_name
    return mapping


def main():
    if len(sys.argv) < 2:
        print("Usage: python inspect_pdf_fields.py <labeled_pdf_path>")
        print("Example: python inspect_pdf_fields.py data/templates/i983_labeled.pdf")
        print("\nWorkflow:")
        print("  1. Fill the PDF with semantic labels (e.g., 'STUDENT_NAME' in name field)")
        print("  2. Run this script on the filled PDF")
        print("  3. Script generates mapping from your labels to PDF field names")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    print(f"Inspecting labeled PDF: {pdf_path}")
    print("-" * 60)
    
    filled_fields = extract_filled_fields(str(pdf_path))
    
    if not filled_fields:
        print("No filled fields found. Make sure you've entered labels into the PDF fields.")
        sys.exit(0)
    
    print(f"Found {len(filled_fields)} filled fields:\n")
    
    # Group by type for display
    by_type: dict[str, list] = {}
    for field_name, props in filled_fields.items():
        ftype = props["type"]
        if ftype not in by_type:
            by_type[ftype] = []
        by_type[ftype].append(props)
    
    for ftype, field_list in sorted(by_type.items()):
        print(f"=== {ftype.upper()} Fields ({len(field_list)}) ===")
        for props in sorted(field_list, key=lambda x: x["semantic_label"]):
            print(f"  {props['semantic_label']}")
            print(f"    -> PDF Field: {props['pdf_field_name']}")
        print()
    
    # Generate and save semantic mapping
    output_dir = pdf_path.parent
    mappings_file = output_dir / "field_mappings.json"
    
    semantic_mapping = generate_semantic_mapping(filled_fields)
    
    # Sort by semantic label for readability
    sorted_mapping = dict(sorted(semantic_mapping.items()))
    
    with open(mappings_file, "w") as f:
        json.dump(sorted_mapping, f, indent=2)
    
    print(f"Semantic mapping saved to: {mappings_file}")
    print(f"\nThe DSOAgent should output JSON with these keys:")
    for label in sorted(semantic_mapping.keys())[:5]:
        print(f"  - {label}")
    if len(semantic_mapping) > 5:
        print(f"  ... and {len(semantic_mapping) - 5} more")


if __name__ == "__main__":
    main()
