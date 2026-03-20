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
