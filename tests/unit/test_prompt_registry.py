from app.services.llm.prompt_registry import get_prompt_spec


def test_prompt_registry_returns_expanded_i20_required_fields():
    spec = get_prompt_spec("i20")

    assert spec.prompt_version == "v2"
    assert spec.required_fields == (
        "sevis_id",
        "surname",
        "given_name",
        "cip_code",
        "major",
        "education_level",
        "school_name",
    )
    assert "grid-like pdf layout" in spec.template.lower()


def test_prompt_registry_returns_expanded_ead_required_fields():
    spec = get_prompt_spec("ead")

    assert spec.prompt_version == "v2"
    assert spec.required_fields == (
        "alien_registration_number",
        "category",
        "card_start_date",
        "card_end_date",
    )
    assert "employment authorization document" in spec.template.lower()


def test_prompt_registry_returns_expanded_offer_letter_required_fields():
    spec = get_prompt_spec("offer_letter")

    assert spec.prompt_version == "v2"
    assert spec.required_fields == (
        "company_name",
        "position_title",
        "job_duties",
        "start_date",
        "hours_per_week",
        "supervisor_name",
        "work_address_street",
        "work_address_city",
        "work_address_state",
        "work_address_zip",
    )
