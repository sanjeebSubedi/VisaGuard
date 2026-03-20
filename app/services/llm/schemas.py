from __future__ import annotations

from pydantic import BaseModel


class I20ExtractionResult(BaseModel):
    sevis_id: str | None = None
    surname: str | None = None
    given_name: str | None = None
    cip_code: str | None = None
    major: str | None = None
    education_level: str | None = None
    school_name: str | None = None
    school_code: str | None = None
    program_start_date: str | None = None
    program_end_date: str | None = None


class EADExtractionResult(BaseModel):
    employment_authorized_until: str | None = None
    ead_category: str | None = None


class OfferLetterExtractionResult(BaseModel):
    employer_name: str | None = None
    job_title: str | None = None
    employment_start_date: str | None = None


SCHEMA_BY_DOCUMENT_TYPE = {
    "i20": I20ExtractionResult,
    "ead": EADExtractionResult,
    "offer_letter": OfferLetterExtractionResult,
}


def get_response_model(document_type: str) -> type[BaseModel]:
    try:
        return SCHEMA_BY_DOCUMENT_TYPE[document_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported document type: {document_type}") from exc
