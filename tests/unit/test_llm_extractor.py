from app.services.llm.extractor import LLMExtractionService


def test_llm_extractor_repairs_json_and_retries_missing_fields(monkeypatch):
    responses = iter(
        [
            '{"sevis_id": "N0035706308"',
            '{"sevis_id": "N0035706308", "surname": null, "given_name": null, "cip_code": null, "major": null, "education_level": null, "school_name": "Example University", "school_code": null, "program_start_date": null, "program_end_date": null}',
            '{"surname": "Subedi", "given_name": "Sanjeeb", "cip_code": "11.0701", "major": "Computer Science", "education_level": "Master\'s"}',
        ]
    )

    monkeypatch.setattr(
        "app.services.llm.extractor.OllamaClientAdapter.generate",
        lambda self, **kwargs: next(responses),
    )

    service = LLMExtractionService(model_name="qwen3:4b-instruct")
    result = service.extract(document_type="i20", parsed_text="doc text")

    assert result.values["sevis_id"] == "N0035706308"
    assert result.values["surname"] == "Subedi"
    assert result.values["given_name"] == "Sanjeeb"
    assert result.values["cip_code"] == "11.0701"
    assert result.values["school_name"] == "Example University"
    assert result.prompt_version == "v2"


def test_llm_extractor_parses_expanded_i20_shape(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm.extractor.OllamaClientAdapter.generate",
        lambda self, **kwargs: '{"sevis_id": "N0035706308", "surname": "Subedi", "given_name": "Sanjeeb", "cip_code": "11.0701", "major": "Computer Science", "education_level": "Master\'s", "school_name": "Example University", "school_code": null, "program_start_date": null, "program_end_date": null}',
    )

    service = LLMExtractionService(model_name="qwen3:4b-instruct")
    result = service.extract(document_type="i20", parsed_text="doc text")

    assert result.values["sevis_id"] == "N0035706308"
    assert result.values["program_end_date"] is None


def test_llm_extractor_trims_i20_context_but_keeps_other_documents_full():
    long_text = "A" * 7000

    i20_prompt = LLMExtractionService._build_prompt("template", "i20", long_text)
    ead_prompt = LLMExtractionService._build_prompt("template", "ead", long_text)

    assert i20_prompt.endswith("A" * 6000)
    assert "A" * 6001 not in i20_prompt
    assert ead_prompt.endswith("A" * 7000)


def test_llm_extractor_merges_offer_letter_multi_call_outputs(monkeypatch):
    responses = iter(
        [
            '{"company_name":"OpenAI","position_title":"Research Intern","start_date":"2026-09-01","hours_per_week":"40","ein":null,"end_date":null,"hourly_rate":null}',
            '{"supervisor_name":"Ada Lovelace","supervisor_email":null,"supervisor_phone":null}',
            '{"job_duties":"Build internal tools","work_address_street":"1 OpenAI Plaza","work_address_city":"San Francisco","work_address_state":"CA","work_address_zip":"94110"}',
            '{"ein":"12-3456789","supervisor_email":"ada@example.com"}',
        ]
    )

    monkeypatch.setattr(
        "app.services.llm.extractor.OllamaClientAdapter.generate",
        lambda self, **kwargs: next(responses),
    )

    service = LLMExtractionService(model_name="qwen3:4b-instruct")
    result = service.extract(document_type="offer_letter", parsed_text="offer letter text")

    assert result.values["company_name"] == "OpenAI"
    assert result.values["position_title"] == "Research Intern"
    assert result.values["job_duties"] == "Build internal tools"
    assert result.values["hours_per_week"] == "40"
    assert result.values["supervisor_name"] == "Ada Lovelace"
    assert result.values["supervisor_email"] == "ada@example.com"
    assert result.values["ein"] == "12-3456789"
    assert result.prompt_version == "v2"
