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
