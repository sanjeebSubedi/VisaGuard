from __future__ import annotations

import json
from dataclasses import dataclass

from app.core.config import Settings
from app.services.llm.ollama_client import OllamaClientAdapter
from app.services.llm.prompt_registry import get_prompt_spec
from app.services.llm.schemas import get_response_model


@dataclass
class LLMExtractionOutcome:
    values: dict[str, str | None]
    raw_json: dict
    prompt_version: str
    model_name: str


class LLMExtractionService:
    def __init__(
        self,
        model_name: str | None = None,
        adapter: OllamaClientAdapter | None = None,
    ) -> None:
        settings = Settings()
        self.model_name = model_name or settings.ollama_model
        self.adapter = adapter or OllamaClientAdapter(
            host=settings.ollama_host,
            timeout_seconds=settings.ollama_timeout_seconds,
        )

    def extract(self, *, document_type: str, parsed_text: str) -> LLMExtractionOutcome:
        prompt_spec = get_prompt_spec(document_type)
        response_model = get_response_model(document_type)

        raw_text = self.adapter.generate(
            model=self.model_name,
            prompt=self._build_prompt(prompt_spec.template, parsed_text),
        )
        payload = self._load_json(raw_text)
        if payload is None:
            repair_text = self.adapter.generate(
                model=self.model_name,
                prompt=self._build_repair_prompt(raw_text),
            )
            payload = self._load_json(repair_text)
            if payload is None:
                raise ValueError("LLM did not return valid JSON")

        parsed = response_model.model_validate(payload)
        values = parsed.model_dump()

        missing_fields = [field for field in prompt_spec.required_fields if values.get(field) is None]
        if missing_fields:
            retry_text = self.adapter.generate(
                model=self.model_name,
                prompt=self._build_missing_fields_prompt(prompt_spec.template, parsed_text, missing_fields),
            )
            retry_payload = self._load_json(retry_text)
            if retry_payload is not None:
                retry_values = response_model.model_validate(retry_payload).model_dump()
                for field in missing_fields:
                    if retry_values.get(field) is not None:
                        values[field] = retry_values[field]

        return LLMExtractionOutcome(
            values=values,
            raw_json=values.copy(),
            prompt_version=prompt_spec.prompt_version,
            model_name=self.model_name,
        )

    @staticmethod
    def _load_json(raw_text: str) -> dict | None:
        try:
            loaded = json.loads(raw_text)
        except json.JSONDecodeError:
            return None
        if not isinstance(loaded, dict):
            return None
        return loaded

    @staticmethod
    def _build_prompt(template: str, parsed_text: str) -> str:
        return f"{template}\n\nDocument text:\n{parsed_text}"

    @staticmethod
    def _build_repair_prompt(raw_text: str) -> str:
        return f"Return valid JSON only for this content:\n{raw_text}"

    @staticmethod
    def _build_missing_fields_prompt(template: str, parsed_text: str, missing_fields: list[str]) -> str:
        fields = ", ".join(missing_fields)
        return f"{template}\n\nReturn only these missing fields in strict JSON: {fields}\n\nDocument text:\n{parsed_text}"
