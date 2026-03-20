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
    assert "few-shot" in spec.template.lower()
