from app.services.validation_rules import validate_extracted_values


def test_validate_extracted_values_marks_missing_required_fields():
    result = validate_extracted_values(
        document_type="ead",
        values={
            "alien_registration_number": "A123456789",
            "category": "C03B",
            "card_start_date": None,
            "card_end_date": "2025-08-14",
        },
    )

    assert "card_start_date" in result.missing_fields


def test_validate_extracted_values_rejects_bad_date_format():
    result = validate_extracted_values(
        document_type="offer_letter",
        values={
            "start_date": "April 27, 2026",
            "position_title": "Backend Software Engineer",
            "company_name": "TechNova",
            "job_duties": "Build services",
            "hours_per_week": "40",
            "supervisor_name": "Ada Lovelace",
            "work_address_street": "1 Main St",
            "work_address_city": "Boston",
            "work_address_state": "MA",
            "work_address_zip": "02110",
        },
    )

    assert "start_date" in result.invalid_fields


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
