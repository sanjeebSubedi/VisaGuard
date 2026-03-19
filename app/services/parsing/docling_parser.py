from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParsedDocument:
    text: str
    metadata: dict
    raw_payload: dict


def _docling_parse(file_bytes: bytes) -> dict:
    text = file_bytes.decode("utf-8", errors="ignore")
    return {"text": text, "pages": 1}


def parse_with_docling(file_bytes: bytes) -> ParsedDocument:
    payload = _docling_parse(file_bytes)
    return ParsedDocument(
        text=payload["text"],
        metadata={"pages": payload.get("pages", 0)},
        raw_payload=payload,
    )
