import pytest

from app.services.parsing.docling_parser import DoclingParseError, ParsedDocument, parse_with_docling


def test_parse_with_docling_uses_pdf_input(monkeypatch):
    monkeypatch.setattr(
        "app.services.parsing.docling_parser._convert_with_docling",
        lambda *, file_bytes, filename, content_type: {
            "text": "Program Start Date: 2026-08-20",
            "metadata": {"pages": 1, "filename": filename, "content_type": content_type},
        },
    )

    parsed = parse_with_docling(file_bytes=b"pdf-bytes", filename="i20.pdf", content_type="application/pdf")

    assert isinstance(parsed, ParsedDocument)
    assert parsed.metadata["pages"] == 1
    assert parsed.metadata["filename"] == "i20.pdf"


def test_parse_with_docling_raises_parse_error(monkeypatch):
    monkeypatch.setattr(
        "app.services.parsing.docling_parser._convert_with_docling",
        lambda **_: (_ for _ in ()).throw(RuntimeError("docling failed")),
    )

    with pytest.raises(DoclingParseError):
        parse_with_docling(file_bytes=b"img", filename="ead.png", content_type="image/png")
