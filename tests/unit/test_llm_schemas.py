from app.services.llm.schemas import (
    EADExtractionResult,
    I20ExtractionResult,
    OfferEmploymentDetailsResult,
    OfferJobLocationResult,
    OfferLetterExtractionResult,
    OfferSupervisorResult,
)


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


def test_ead_schema_supports_expanded_field_set():
    result = EADExtractionResult.model_validate(
        {
            "alien_registration_number": "A123456789",
            "category": "C03B",
            "card_start_date": "2024-08-15",
            "card_end_date": "2025-08-14",
            "card_number": None,
        }
    )

    assert result.alien_registration_number == "A123456789"
    assert result.category == "C03B"
    assert result.card_number is None


def test_offer_letter_schema_supports_expanded_field_set():
    result = OfferLetterExtractionResult.model_validate(
        {
            "company_name": "OpenAI",
            "position_title": "Research Intern",
            "job_duties": "Build internal tools",
            "start_date": "2026-09-01",
            "hours_per_week": "40",
            "supervisor_name": "Ada Lovelace",
            "work_address_street": "1 OpenAI Plaza",
            "work_address_city": "San Francisco",
            "work_address_state": "CA",
            "work_address_zip": "94110",
            "ein": None,
            "end_date": None,
            "hourly_rate": None,
            "supervisor_email": None,
            "supervisor_phone": None,
        }
    )

    assert result.company_name == "OpenAI"
    assert result.hours_per_week == "40"
    assert result.supervisor_email is None


def test_offer_letter_subschemas_support_multi_call_outputs():
    employment = OfferEmploymentDetailsResult.model_validate(
        {
            "company_name": "OpenAI",
            "position_title": "Research Intern",
            "start_date": "2026-09-01",
            "hours_per_week": "40",
            "ein": None,
            "end_date": None,
            "hourly_rate": None,
        }
    )
    supervisor = OfferSupervisorResult.model_validate(
        {
            "supervisor_name": "Ada Lovelace",
            "supervisor_email": None,
            "supervisor_phone": None,
        }
    )
    job_location = OfferJobLocationResult.model_validate(
        {
            "job_duties": "Build internal tools",
            "work_address_street": "1 OpenAI Plaza",
            "work_address_city": "San Francisco",
            "work_address_state": "CA",
            "work_address_zip": "94110",
        }
    )

    assert employment.company_name == "OpenAI"
    assert supervisor.supervisor_name == "Ada Lovelace"
    assert job_location.work_address_zip == "94110"


def test_offer_letter_schemas_coerce_numeric_hours_and_rates_to_strings():
    employment = OfferEmploymentDetailsResult.model_validate(
        {
            "company_name": "OpenAI",
            "position_title": "Research Intern",
            "start_date": "2026-09-01",
            "hours_per_week": 40,
            "hourly_rate": 38.5,
        }
    )
    offer = OfferLetterExtractionResult.model_validate(
        {
            "company_name": "OpenAI",
            "position_title": "Research Intern",
            "job_duties": "Build internal tools",
            "start_date": "2026-09-01",
            "hours_per_week": 40,
            "supervisor_name": "Ada Lovelace",
            "work_address_street": "1 OpenAI Plaza",
            "work_address_city": "San Francisco",
            "work_address_state": "CA",
            "work_address_zip": "94110",
            "hourly_rate": 38.5,
        }
    )

    assert employment.hours_per_week == "40"
    assert employment.hourly_rate == "38.5"
    assert offer.hours_per_week == "40"
    assert offer.hourly_rate == "38.5"
