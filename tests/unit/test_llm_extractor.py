from app.services.llm.extractor import LLMExtractionService


def test_llm_extractor_repairs_json_and_retries_missing_fields(monkeypatch):
    responses = iter(
        [
            '{"program_start_date": "2026-08-20"',
            '{"program_start_date": null, "cip_code": null, "school_name": "Example University"}',
            '{"program_start_date": "2026-08-20", "cip_code": "11.0701"}',
        ]
    )

    monkeypatch.setattr(
        "app.services.llm.extractor.OllamaClientAdapter.generate",
        lambda self, **kwargs: next(responses),
    )

    service = LLMExtractionService(model_name="qwen3:4b-instruct")
    result = service.extract(document_type="i20", parsed_text="doc text")

    assert result.values["program_start_date"] == "2026-08-20"
    assert result.values["cip_code"] == "11.0701"
    assert result.values["school_name"] == "Example University"
    assert result.prompt_version == "v1"
