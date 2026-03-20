from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.services.llm.ollama_client import OllamaClientAdapter
from app.services.llm.prompt_registry import get_prompt_spec
from app.services.llm.schemas import (
    OfferEmploymentDetailsResult,
    OfferJobLocationResult,
    OfferLetterExtractionResult,
    OfferSupervisorResult,
    get_response_model,
)


@dataclass
class LLMExtractionOutcome:
    values: dict[str, str | None]
    raw_json: dict
    prompt_version: str
    model_name: str


class LLMExtractionService:
    I20_CONTEXT_LIMIT = 6000
    OFFER_PROMPT_DIR = Path(__file__).with_name("prompts") / "offer_letter"

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
        if document_type == "offer_letter":
            return self._extract_offer_letter(parsed_text=parsed_text)

        prompt_spec = get_prompt_spec(document_type)
        response_model = get_response_model(document_type)

        payload = self._generate_payload(
            model_name=self.model_name,
            prompt=self._build_prompt(prompt_spec.template, document_type, parsed_text),
        )
        parsed = response_model.model_validate(payload)
        values = parsed.model_dump()

        missing_fields = [field for field in prompt_spec.required_fields if values.get(field) is None]
        if missing_fields:
            retry_payload = self._generate_payload(
                model_name=self.model_name,
                prompt=self._build_missing_fields_prompt(
                    prompt_spec.template,
                    document_type,
                    parsed_text,
                    missing_fields,
                ),
            )
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

    def _extract_offer_letter(self, *, parsed_text: str) -> LLMExtractionOutcome:
        prompt_spec = get_prompt_spec("offer_letter")
        employment_payload = self._generate_payload(
            model_name=self.model_name,
            prompt=self._build_offer_prompt("employment_details.txt", parsed_text=parsed_text),
        )
        supervisor_payload = self._generate_payload(
            model_name=self.model_name,
            prompt=self._build_offer_prompt("supervisor_details.txt", parsed_text=parsed_text),
        )
        job_location_payload = self._generate_payload(
            model_name=self.model_name,
            prompt=self._build_offer_prompt("job_location.txt", parsed_text=parsed_text),
        )

        values = {
            **OfferEmploymentDetailsResult.model_validate(employment_payload).model_dump(),
            **OfferSupervisorResult.model_validate(supervisor_payload).model_dump(),
            **OfferJobLocationResult.model_validate(job_location_payload).model_dump(),
        }
        values = OfferLetterExtractionResult.model_validate(values).model_dump()

        recovery_fields = [field for field, value in values.items() if value is None]
        recovery_payload = None
        if recovery_fields:
            recovery_payload = self._generate_payload(
                model_name=self.model_name,
                prompt=self._build_offer_recovery_prompt(parsed_text=parsed_text, missing_fields=recovery_fields),
            )
            recovery_values = OfferLetterExtractionResult.model_validate(recovery_payload).model_dump()
            for field in recovery_fields:
                if recovery_values.get(field) is not None:
                    values[field] = recovery_values[field]

        return LLMExtractionOutcome(
            values=values,
            raw_json={
                "employment_details": employment_payload,
                "supervisor_details": supervisor_payload,
                "job_location": job_location_payload,
                "recovery": recovery_payload,
            },
            prompt_version=prompt_spec.prompt_version,
            model_name=self.model_name,
        )

    def _generate_payload(self, *, model_name: str, prompt: str) -> dict:
        raw_text = self.adapter.generate(model=model_name, prompt=prompt)
        payload = self._load_json(raw_text)
        if payload is None:
            repair_text = self.adapter.generate(
                model=model_name,
                prompt=self._build_repair_prompt(raw_text),
            )
            payload = self._load_json(repair_text)
            if payload is None:
                raise ValueError("LLM did not return valid JSON")
        return payload

    @classmethod
    def _build_offer_prompt(cls, prompt_name: str, *, parsed_text: str) -> str:
        template = (cls.OFFER_PROMPT_DIR / prompt_name).read_text()
        return template.format(text=parsed_text)

    @classmethod
    def _build_offer_recovery_prompt(cls, *, parsed_text: str, missing_fields: list[str]) -> str:
        template = (cls.OFFER_PROMPT_DIR / "recovery.txt").read_text()
        return template.format(
            missing_fields="\n".join(f"- {field}" for field in missing_fields),
            text=parsed_text,
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
    def _trim_context(document_type: str, parsed_text: str) -> str:
        if document_type == "i20":
            return parsed_text[: LLMExtractionService.I20_CONTEXT_LIMIT]
        return parsed_text

    @staticmethod
    def _build_prompt(template: str, document_type: str, parsed_text: str) -> str:
        context = LLMExtractionService._trim_context(document_type, parsed_text)
        return f"{template}\n\nDocument text:\n{context}"

    @staticmethod
    def _build_repair_prompt(raw_text: str) -> str:
        return f"Return valid JSON only for this content:\n{raw_text}"

    @staticmethod
    def _build_missing_fields_prompt(
        template: str,
        document_type: str,
        parsed_text: str,
        missing_fields: list[str],
    ) -> str:
        fields = ", ".join(missing_fields)
        context = LLMExtractionService._trim_context(document_type, parsed_text)
        return f"{template}\n\nReturn only these missing fields in strict JSON: {fields}\n\nDocument text:\n{context}"
