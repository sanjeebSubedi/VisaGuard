from app.services.llm.schemas import I20ExtractionResult


def test_i20_schema_accepts_null_optional_fields():
    result = I20ExtractionResult.model_validate(
        {
            "program_start_date": "2026-08-20",
            "cip_code": None,
            "school_name": "Example University",
        }
    )

    assert result.cip_code is None
