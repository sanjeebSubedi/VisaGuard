from app.services.llm.prompt_registry import get_prompt_spec


def test_prompt_registry_returns_i20_prompt_spec():
    spec = get_prompt_spec("i20")

    assert spec.prompt_version == "v1"
    assert "program_start_date" in spec.required_fields
    assert "strict JSON" in spec.template
