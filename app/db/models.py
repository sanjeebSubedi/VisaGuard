"""
SQLModel database models for document storage.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class I20Document(SQLModel, table=True):
    """I-20 (Certificate of Eligibility) document record."""

    __tablename__ = "i20_documents"

    id: int | None = Field(default=None, primary_key=True)
    file_path: str = Field(index=True)
    file_hash: str = Field(index=True, unique=True)  # SHA-256 hex digest

    # Extracted fields
    sevis_id: str = Field(index=True)
    surname: str
    given_name: str
    program_start: str | None = None
    program_end: str | None = None
    major: str
    cip_code: str | None = None
    education_level: str
    school: str

    created_at: datetime = Field(default_factory=datetime.utcnow)


class OfferLetterDocument(SQLModel, table=True):
    """Employment Offer Letter document record."""

    __tablename__ = "offer_letter_documents"

    id: int | None = Field(default=None, primary_key=True)
    file_path: str = Field(index=True)
    file_hash: str = Field(index=True, unique=True)  # SHA-256 hex digest

    # Company info
    company_name: str
    ein: str | None = None

    # Job details
    position_title: str
    job_duties_text: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    hours_per_week: float | None = None
    salary_amount: float | None = None
    salary_frequency: str | None = None

    # Supervisor
    supervisor_name: str | None = None
    supervisor_title: str | None = None
    supervisor_email: str | None = None
    supervisor_phone: str | None = None

    # Work location
    work_address_street: str | None = None
    work_address_city: str | None = None
    work_address_state: str | None = None
    work_address_zip: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class EADDocument(SQLModel, table=True):
    """Employment Authorization Document (EAD) record."""

    __tablename__ = "ead_documents"

    id: int | None = Field(default=None, primary_key=True)
    file_path: str = Field(index=True)
    file_hash: str = Field(index=True, unique=True)  # SHA-256 hex digest

    # Card fields
    uscis_number: str = Field(index=True)
    category_code: str
    card_start_date: str
    card_end_date: str

    created_at: datetime = Field(default_factory=datetime.utcnow)
