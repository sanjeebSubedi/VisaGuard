from app.services.validation_rules import validate_extracted_values


def test_validate_extracted_values_marks_missing_required_fields():
    result = validate_extracted_values(
        document_type="ead",
        values={"employment_authorized_until": None, "ead_category": "C03B"},
    )

    assert "employment_authorized_until" in result.missing_fields


def test_validate_extracted_values_rejects_bad_date_format():
    result = validate_extracted_values(
        document_type="offer_letter",
        values={
            "employment_start_date": "April 27, 2026",
            "job_title": "Backend Software Engineer",
            "employer_name": "TechNova",
        },
    )

    assert "employment_start_date" in result.invalid_fields


def test_validate_extracted_values_allows_missing_optional_i20_fields():
    result = validate_extracted_values(
        document_type="i20",
        values={
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
        },
    )

    assert result.missing_fields == []
