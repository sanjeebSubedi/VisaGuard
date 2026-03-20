from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import ThreadedPdfPipelineOptions
from docling.document_converter import DocumentConverter, ImageFormatOption, PdfFormatOption
from docling_core.types.io import DocumentStream


@dataclass
class ParsedDocument:
    text: str
    metadata: dict
    raw_payload: dict


class DoclingParseError(RuntimeError):
    pass


def _build_cpu_format_options() -> dict[InputFormat, PdfFormatOption | ImageFormatOption]:
    pipeline_options = ThreadedPdfPipelineOptions(
        accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU),
    )
    return {
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline_options),
    }


def _convert_with_docling(*, file_bytes: bytes, filename: str, content_type: str) -> dict:
    converter = DocumentConverter(format_options=_build_cpu_format_options())
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
