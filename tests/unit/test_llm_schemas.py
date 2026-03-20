from app.services.llm.schemas import I20ExtractionResult


def test_i20_schema_supports_expanded_field_set():
    result = I20ExtractionResult.model_validate(
        {
            "sevis_id": "N0035706308",
            "surname": "Subedi",
            "given_name": "Sanjeeb",
            "cip_code": "11.0701",
            "major": "Computer Science",
            "education_level": "Master's",
            "school_name": "Example University",
            "school_code": None,
            "program_start_date": None,
            "program_end_date": None,
        }
    )

    assert result.sevis_id == "N0035706308"
    assert result.school_code is None
    assert result.program_end_date is None
