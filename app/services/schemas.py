"""
Pydantic schemas for document field extraction and PII redaction.

These schemas define the structured output format for LLM extraction.
"""

from typing import Optional

from pydantic import BaseModel, Field


class I20Fields(BaseModel):
    """Fields extracted from I-20 (Certificate of Eligibility)."""

    sevis_id: str = Field(description="SEVIS ID (N followed by 10 digits)")
    surname: str = Field(description="Student's family/last name")
    given_name: str = Field(description="Student's first name")

    program_start: Optional[str] = Field(default=None, description="Program start date")
    program_end: Optional[str] = Field(default=None, description="Program end date")

    major: str = Field(description="Major/field of study")
    cip_code: Optional[str] = Field(description="The numeric CIP code (e.g., 11.0701)")
    education_level: str = Field(description="Education level")
    school: str = Field(description="School/university name")


class OfferLetterFields(BaseModel):
    """
    Fields extracted from an Employment Offer Letter.
    Designed to populate I-983 Sections 3 (Employer) and 5 (Training Plan).
    """

    # Employer Details
    company_name: str = Field(description="Full legal name of the employer")
    ein: Optional[str] = Field(None, description="Employer Identification Number")

    # Job Details
    position_title: str = Field(description="Job title (e.g., 'Software Engineer')")
    job_duties_text: str = Field(
        ...,
        description="The FULL text block describing job responsibilities. Do not summarize.",
    )

    # Timeline & Compensation (Critical for Compliance)
    start_date: str = Field(description="Employment start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(
        None, description="Employment end date (if specified)"
    )
    hours_per_week: float = Field(..., description="Number of hours per week (numeric)")
    salary_amount: Optional[float] = Field(
        None, description="Salary amount (numeric only)"
    )
    salary_frequency: Optional[str] = Field(
        None, description="Frequency (e.g., 'Year', 'Hour', 'Month')"
    )

    # Supervisor Info (Critical for I-983 Section 5)
    # Often found in "Reports to..." or signature lines
    supervisor_name: Optional[str] = Field(
        None, description="Name of the direct supervisor or hiring manager"
    )
    supervisor_title: Optional[str] = Field(
        None, description="Job title of the supervisor"
    )
    supervisor_email: Optional[str] = Field(
        None, description="Email address of the supervisor"
    )
    supervisor_phone: Optional[str] = Field(
        None, description="Phone number of the supervisor"
    )

    work_address_street: Optional[str] = Field(
        None, description="Street address of work location"
    )
    work_address_city: Optional[str] = Field(None, description="City")
    work_address_state: Optional[str] = Field(
        None, description="State code (e.g., CA, NY)"
    )
    work_address_zip: Optional[str] = Field(None, description="Zip code")


# =============================================================================
# FOCUSED SUB-SCHEMAS FOR MULTI-CALL EXTRACTION
# =============================================================================

class OfferEmploymentDetails(BaseModel):
    """Focused extraction: Employment details only."""
    company_name: str = Field(description="Full legal name of the employer")
    ein: Optional[str] = Field(None, description="Employer Identification Number (XX-XXXXXXX format)")
    position_title: str = Field(description="Job title")
    start_date: str = Field(description="Employment start date")
    end_date: Optional[str] = Field(None, description="Employment end date")
    hours_per_week: float = Field(description="Weekly hours (numeric)")
    salary_amount: Optional[float] = Field(None, description="Salary amount (numeric)")
    salary_frequency: Optional[str] = Field(None, description="Hour, Month, or Year")


class OfferSupervisorInfo(BaseModel):
    """Focused extraction: Supervisor info only."""
    supervisor_name: Optional[str] = Field(None, description="Supervisor's full name")
    supervisor_title: Optional[str] = Field(None, description="Supervisor's job title")
    supervisor_email: Optional[str] = Field(None, description="Supervisor's email")
    supervisor_phone: Optional[str] = Field(None, description="Supervisor's phone")


class OfferJobAndLocation(BaseModel):
    """Focused extraction: Job duties and work location together."""
    job_duties_text: str = Field(description="Full text of job duties/responsibilities")
    work_street: Optional[str] = Field(None, description="Street address of work location")
    work_city: Optional[str] = Field(None, description="City")
    work_state: Optional[str] = Field(None, description="State code (e.g., CA)")
    work_zip: Optional[str] = Field(None, description="Zip code")


class EADFields(BaseModel):
    uscis_number: str = Field(description="USCIS# without hyphens")
    category_code: str = Field(description="e.g. C03B, C03C")
    card_start_date: str = Field(description="Date labeled 'Valid From'")  # Added this!
    card_end_date: str = Field(description="Date labeled 'Card Expires'")
