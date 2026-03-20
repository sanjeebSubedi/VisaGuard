from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from docling.document_converter import DocumentConverter
from docling_core.types.io import DocumentStream


@dataclass
class ParsedDocument:
    text: str
    metadata: dict
    raw_payload: dict


class DoclingParseError(RuntimeError):
    pass


def _convert_with_docling(*, file_bytes: bytes, filename: str, content_type: str) -> dict:
    converter = DocumentConverter()
    stream = DocumentStream(name=filename, stream=BytesIO(file_bytes))
    result = converter.convert(stream)
    return {
        "text": result.document.export_to_markdown(),
        "metadata": {
            "pages": result.input.page_count or 0,
            "filename": filename,
            "content_type": content_type,
            "status": str(result.status),
        },
    }


def parse_with_docling(*, file_bytes: bytes, filename: str, content_type: str) -> ParsedDocument:
    try:
        payload = _convert_with_docling(file_bytes=file_bytes, filename=filename, content_type=content_type)
    except Exception as exc:
        raise DoclingParseError(str(exc)) from exc

    return ParsedDocument(
        text=payload["text"],
        metadata=payload["metadata"],
        raw_payload={},
    )
