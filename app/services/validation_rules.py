from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.llm.prompt_registry import get_prompt_spec


DATE_FIELDS = {"program_start_date", "employment_authorized_until", "employment_start_date"}


@dataclass
class ValidationResult:
    missing_fields: list[str] = field(default_factory=list)
    invalid_fields: list[str] = field(default_factory=list)


def validate_extracted_values(document_type: str, values: dict[str, str | None]) -> ValidationResult:
    prompt_spec = get_prompt_spec(document_type)
    result = ValidationResult()

    for field_name in prompt_spec.required_fields:
        value = values.get(field_name)
        if value is None:
            result.missing_fields.append(field_name)
            continue
        if field_name in DATE_FIELDS and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            result.invalid_fields.append(field_name)

    return result
