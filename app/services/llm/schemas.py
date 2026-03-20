from __future__ import annotations

from pydantic import BaseModel, field_validator


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
    alien_registration_number: str | None = None
    category: str | None = None
    card_start_date: str | None = None
    card_end_date: str | None = None
    card_number: str | None = None


class OfferLetterExtractionResult(BaseModel):
    company_name: str | None = None
    position_title: str | None = None
    job_duties: str | None = None
    start_date: str | None = None
    hours_per_week: str | None = None
    supervisor_name: str | None = None
    work_address_street: str | None = None
    work_address_city: str | None = None
    work_address_state: str | None = None
    work_address_zip: str | None = None
    ein: str | None = None
    end_date: str | None = None
    hourly_rate: str | None = None
    supervisor_email: str | None = None
    supervisor_phone: str | None = None

    @field_validator("hours_per_week", "hourly_rate", mode="before")
    @classmethod
    def _coerce_numeric_strings(cls, value: str | int | float | None) -> str | None:
        if value is None:
            return None
        return str(value)


class OfferEmploymentDetailsResult(BaseModel):
    company_name: str | None = None
    position_title: str | None = None
    start_date: str | None = None
    hours_per_week: str | None = None
    ein: str | None = None
    end_date: str | None = None
    hourly_rate: str | None = None

    @field_validator("hours_per_week", "hourly_rate", mode="before")
    @classmethod
    def _coerce_numeric_strings(cls, value: str | int | float | None) -> str | None:
        if value is None:
            return None
        return str(value)


class OfferSupervisorResult(BaseModel):
    supervisor_name: str | None = None
    supervisor_email: str | None = None
    supervisor_phone: str | None = None


class OfferJobLocationResult(BaseModel):
    job_duties: str | None = None
    work_address_street: str | None = None
    work_address_city: str | None = None
    work_address_state: str | None = None
    work_address_zip: str | None = None


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
