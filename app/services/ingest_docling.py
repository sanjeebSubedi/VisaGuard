"""
Document Ingestion Service with Docling

Handles PDF/image to text conversion using Docling.
Field extraction and PII redaction will be handled by LLM (Phi-3.5 Mini).
"""

from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableFormerMode,
    TableStructureOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption


def ingest_document(file_path: str) -> str:
    """
    Parse a document with Docling and return the extracted text.
    
    Args:
        file_path: Path to the document (PDF or image)
    
    Returns:
        Extracted text in markdown format
    """
    path = Path(file_path)
    ext = path.suffix.lower()
    
    # Configure converter based on file type
    if ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
        converter = DocumentConverter()
    else:
        # PDF with table extraction
        pdf_options = PdfPipelineOptions()
        pdf_options.do_table_structure = True
        pdf_options.table_structure_options = TableStructureOptions(
            do_cell_matching=True,
            mode=TableFormerMode.ACCURATE
        )
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)
            }
        )
    
    # Convert and return text
    result = converter.convert(file_path)
    return result.document.export_to_markdown()


if __name__ == "__main__":
    # Quick test
    FILE = "data/templates/i20.pdf"
    
    print(f"Parsing: {FILE}")
    print("=" * 50)
    
    text = ingest_document(FILE)
    print(f"Extracted {len(text)} characters")
    print("-" * 50)
    print(text[:1000] + "..." if len(text) > 1000 else text)
