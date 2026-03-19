from app.services.parsing.docling_parser import ParsedDocument, parse_with_docling


def test_parse_with_docling_returns_text_and_metadata(monkeypatch):
    monkeypatch.setattr(
        "app.services.parsing.docling_parser._docling_parse",
        lambda _bytes: {"text": "Program Start Date: 2026-08-20", "pages": 1},
    )

    parsed = parse_with_docling(b"pdf bytes")

    assert isinstance(parsed, ParsedDocument)
    assert "Program Start Date" in parsed.text
    assert parsed.metadata["pages"] == 1
