from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PromptSpec:
    document_type: str
    template: str
    prompt_version: str
    required_fields: tuple[str, ...]


PROMPT_DIR = Path(__file__).with_name("prompts")

PROMPT_SPECS = {
    "i20": PromptSpec(
        document_type="i20",
        template=(PROMPT_DIR / "i20.txt").read_text(),
        prompt_version="v2",
        required_fields=(
            "sevis_id",
            "surname",
            "given_name",
            "cip_code",
            "major",
            "education_level",
            "school_name",
        ),
    ),
    "ead": PromptSpec(
        document_type="ead",
        template=(PROMPT_DIR / "ead.txt").read_text(),
        prompt_version="v1",
        required_fields=("employment_authorized_until", "ead_category"),
    ),
    "offer_letter": PromptSpec(
        document_type="offer_letter",
        template=(PROMPT_DIR / "offer_letter.txt").read_text(),
        prompt_version="v1",
        required_fields=("employer_name", "job_title", "employment_start_date"),
    ),
}


def get_prompt_spec(document_type: str) -> PromptSpec:
    try:
        return PROMPT_SPECS[document_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported document type: {document_type}") from exc
