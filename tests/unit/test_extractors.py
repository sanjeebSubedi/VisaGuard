from app.services.extractors.router import get_extractor


def test_get_extractor_returns_i20_extractor():
    extractor = get_extractor("i20")
    facts = extractor.extract("Program Start Date: 2026-08-20\nCIP Code: 11.0101")

    field_names = {fact.field_name for fact in facts}
    assert "program_start_date" in field_names
    assert "cip_code" in field_names
