"""
Document processors for VisaGuard.

Each document type has a specialized processor that:
- Parses the document with Docling
- Extracts required fields using LLM with structured output

Design:
- I-20, EAD: Fields-only (no text storage)
- Offer Letter: Fields + redacted text for RAG
"""

from langchain_ollama import ChatOllama

from app.services.ingest_docling import ingest_document
from app.services.schemas import EADFields, I20Fields, OfferLetterFields

# LLM configuration
MODEL_NAME = "qwen3:4b-instruct"
TEMPERATURE = 0


def get_llm() -> ChatOllama:
    """Get the Ollama LLM instance."""
    return ChatOllama(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
    )


def _manual_normalize(data: dict) -> dict:
    """Fallback manual normalization for dates and fields."""
    import re
    from datetime import datetime

    result = data.copy()

    # Date patterns to try
    date_patterns = [
        (r"(\w+)\s+(\d{1,2}),?\s+(\d{4})", "%B %d %Y"),  # January 31, 2027
        (r"(\d{1,2})\s+(\w+)\s+(\d{4})", "%d %B %Y"),  # 31 January 2027
        (r"(\d{4})-(\d{2})-(\d{2})", None),  # Already YYYY-MM-DD
    ]

    def normalize_date(value):
        if not value or not isinstance(value, str):
            return value

        # Already in correct format
        if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            return value

        # Try to parse and reformat
        for pattern, fmt in date_patterns:
            if fmt and re.search(pattern, value):
                try:
                    # Clean the value
                    clean_val = re.sub(r",", "", value).strip()
                    dt = datetime.strptime(clean_val, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue

        return value  # Return original if can't parse

    # Normalize date fields
    date_fields = [
        "start_date",
        "end_date",
        "program_start",
        "program_end",
        "card_start_date",
        "card_end_date",
    ]
    for field in date_fields:
        if field in result:
            result[field] = normalize_date(result[field])

    return result


# =============================================================================
# I-20 PROCESSOR (Fields Only)
# =============================================================================

I20_EXTRACTION_PROMPT = """You are an expert document parser for US Immigration Forms (I-20).
Your goal is to extract structured data accurately, even if the text layout is jumbled.

### The Problem: Grid Layouts
The text comes from a PDF where columns often merge.
* *Bad Parse:* "DATE OF BIRTH ADMISSION NUMBER 05 FEB 1999 123456789"
* *Your Job:* Disentangle which value belongs to which label.

### Instructions:
1.  **Analyze First:** Before outputting JSON, use `<analysis>` tags to locate each field.
2.  **Find Anchors:**
    * **Date of Birth:** Look for the pattern `DD MONTH YYYY` (e.g., 07 NOVEMBER 2001). It is usually *near* the label "DATE OF BIRTH" but might be separated by other text.
    * **Country of Birth:** Look for a country name *near* "COUNTRY OF BIRTH". Distinguish it from "COUNTRY OF CITIZENSHIP".
    * **SEVIS ID:** Look for `N` followed by 10 digits at the top of the text.
3.  **Output JSON:** After your analysis, output the valid JSON object.

### Example Thinking Process:
Input: "SURNAME/PRIMARY NAME SMITH GIVEN NAME JOHN DATE OF BIRTH 01 JANUARY 2000"
<analysis>
- Searching for Surname... Found "SMITH" after "SURNAME/PRIMARY NAME".
- Searching for Date of Birth... Found "01 JANUARY 2000" (matches Date pattern).
- Assigning values to fields.
</analysis>
{{
  "surname": "SMITH",
  "date_of_birth": "01 JANUARY 2000",
  ...
}}

### Document Text:
{text}
"""


def process_i20(file_path: str) -> I20Fields:
    """
    Process an I-20 document and extract required fields.

    Args:
        file_path: Path to the I-20 PDF

    Returns:
        I20Fields with extracted data
    """
    # Step 1: Parse PDF to text
    text = ingest_document(file_path)

    # Step 2: Extract fields with LLM
    llm = get_llm()
    structured_llm = llm.with_structured_output(I20Fields)

    # Use first 6000 chars (fields are at the top of the document)
    text_sample = text[:6000] if len(text) > 6000 else text
    prompt = I20_EXTRACTION_PROMPT.format(text=text_sample)

    result = structured_llm.invoke(prompt)
    return result


# =============================================================================
# EAD PROCESSOR (Fields Only)
# =============================================================================

EAD_EXTRACTION_PROMPT = """You are a specialized data extraction engine for US Immigration Documents.
Your task is to extract structured data from an **Employment Authorization Document (EAD)** (Form I-766).

### Critical Layout Hints:
1. **Dates are Critical:** Look for **two** distinct dates on the front of the card:
   - "Valid From" (Start Date) -> extract as `card_start_date`
   - "Card Expires" (End Date) -> extract as `card_end_date`
   - Format: Convert all dates to **YYYY-MM-DD**.
2. **Category Code:** Look for the code under the "Category" label.
   - For OPT students, this is usually **C03A** (Pre-completion), **C03B** (Post-completion), or **C03C** (STEM Extension).
3. **USCIS #:** This is the same as the A-Number. It is usually labeled "USCIS#" and formatted like `XXX-XXX-XXX`.
   - Remove the hyphens.
   - If it starts with "A", include the "A".

### Extraction Rules:
- Return ONLY the values.
- If a field is not found, return null.
- Do not extract the "Card #" (WAC/IOE...) unless explicitly asked, do not confuse it with the USCIS#.

### Input Document:
{text}
"""


def process_ead(file_path: str) -> EADFields:
    """
    Process an EAD card image and extract required fields.

    Args:
        file_path: Path to the EAD image (PNG/JPG)

    Returns:
        EADFields with extracted data
    """
    text = ingest_document(file_path)

    llm = get_llm()
    structured_llm = llm.with_structured_output(EADFields)

    prompt = EAD_EXTRACTION_PROMPT.format(text=text)
    result = structured_llm.invoke(prompt)
    return result


# =============================================================================
# OFFER LETTER PROCESSOR (Multi-Call Focused Extraction)
# =============================================================================

# Focused prompts for each extraction call

EMPLOYMENT_DETAILS_PROMPT = """Extract employment details from this offer letter.

Look for:
- Company name (the employer)
- EIN: Format XX-XXXXXXX (return null if not found)
- Position/Job title
- Start Date (Employment start). Ignore "Offer Expiration Date".
- End Date (Employment end). Return null if "At-Will" or indefinite.
- Hours per week (numeric). If "Full-Time" and no number listed, return 40.
- Salary amount and frequency (e.g., "$XX per hour" → amount=XX, frequency="Hour")

Document:
{text}
"""

SUPERVISOR_PROMPT = """Extract the SUPERVISOR information.

Priority Order:
1. Look for a specific "Supervision" or "Reports to" section. (Primary Source)
2. IF AND ONLY IF that is missing, extract the person who signed the letter (Signatory) as the supervisor.

Extract:
- Name
- Job Title
- Email
- Phone

Document:
{text}
"""

JOB_AND_LOCATION_PROMPT = """Extract job duties and work location from this offer letter.

**Job Duties:**
Look for "Job Description", "Responsibilities", or "Duties" section.
Copy the ENTIRE text including all bullet points. Do not summarize.

**Work Location:**
Look for "Work Location:" or the company address.
Split into: street, city, state, zip

Document:
{text}
"""


def process_offer_letter(file_path: str) -> OfferLetterFields:
    """
    Process an offer letter using 3 focused LLM calls + recovery pass.
    """
    import re
    from typing import Optional

    from pydantic import BaseModel, Field

    from app.services.schemas import (
        OfferEmploymentDetails,
        OfferJobAndLocation,
        OfferSupervisorInfo,
    )

    text = ingest_document(file_path)
    llm = get_llm()

    # Call 1: Employment Details
    emp_llm = llm.with_structured_output(OfferEmploymentDetails)
    emp_result = emp_llm.invoke(EMPLOYMENT_DETAILS_PROMPT.format(text=text))

    # Call 2: Supervisor Info
    sup_llm = llm.with_structured_output(OfferSupervisorInfo)
    sup_result = sup_llm.invoke(SUPERVISOR_PROMPT.format(text=text))

    # Call 3: Job Duties + Work Location
    job_loc_llm = llm.with_structured_output(OfferJobAndLocation)
    job_loc_result = job_loc_llm.invoke(JOB_AND_LOCATION_PROMPT.format(text=text))

    # Regex fallback for EIN if LLM missed it
    ein = emp_result.ein
    if not ein:
        ein_match = re.search(r"\b(\d{2}-\d{7})\b", text)
        if ein_match:
            ein = ein_match.group(1)

    # Collect missing fields
    missing_fields = []
    if not ein:
        missing_fields.append(
            "ein (Employer Identification Number, format: XX-XXXXXXX)"
        )
    if not emp_result.end_date:
        missing_fields.append("end_date (Employment end date)")
    if not sup_result.supervisor_name:
        missing_fields.append("supervisor_name")
    if not sup_result.supervisor_email:
        missing_fields.append("supervisor_email")

    # If there are missing fields, do a recovery pass
    recovered = {}
    if missing_fields:
        # Build dynamic schema for missing fields
        class MissingFieldsRecovery(BaseModel):
            ein: Optional[str] = Field(None, description="EIN (XX-XXXXXXX format)")
            end_date: Optional[str] = Field(None, description="Employment end date")
            supervisor_name: Optional[str] = Field(
                None, description="Supervisor's name"
            )
            supervisor_email: Optional[str] = Field(
                None, description="Supervisor's email"
            )

        recovery_prompt = f"""The following fields were NOT found in the first extraction pass.
Search the document VERY CAREFULLY to find them:

Missing fields:
{chr(10).join("- " + f for f in missing_fields)}

Search hints:
- EIN: Look for "Employer Identification Number", "EIN:", or "Tax ID:" followed by XX-XXXXXXX format
- end_date: Look for "End Date:", "Employment ends", or date after "through"
- supervisor: Look in "Supervision" section, "Reports to", or letter signatory

Document:
{text}
"""
        recovery_llm = llm.with_structured_output(MissingFieldsRecovery)
        recovery_result = recovery_llm.invoke(recovery_prompt)

        # Apply recovered values
        if recovery_result.ein and not ein:
            ein = recovery_result.ein
        if recovery_result.end_date and not emp_result.end_date:
            recovered["end_date"] = recovery_result.end_date
        if recovery_result.supervisor_name and not sup_result.supervisor_name:
            recovered["supervisor_name"] = recovery_result.supervisor_name
        if recovery_result.supervisor_email and not sup_result.supervisor_email:
            recovered["supervisor_email"] = recovery_result.supervisor_email

    # Combine results into preliminary dict
    raw_data = {
        "company_name": emp_result.company_name,
        "ein": ein,
        "position_title": emp_result.position_title,
        "job_duties_text": job_loc_result.job_duties_text,
        "start_date": emp_result.start_date,
        "end_date": recovered.get("end_date", emp_result.end_date),
        "hours_per_week": emp_result.hours_per_week,
        "salary_amount": emp_result.salary_amount,
        "salary_frequency": emp_result.salary_frequency,
        "supervisor_name": recovered.get("supervisor_name", sup_result.supervisor_name),
        "supervisor_title": sup_result.supervisor_title,
        "supervisor_email": recovered.get(
            "supervisor_email", sup_result.supervisor_email
        ),
        "supervisor_phone": sup_result.supervisor_phone,
        "work_address_street": job_loc_result.work_street,
        "work_address_city": job_loc_result.work_city,
        "work_address_state": job_loc_result.work_state,
        "work_address_zip": job_loc_result.work_zip,
    }

    # Normalize dates and clean fields
    normalized = _manual_normalize(raw_data)

    return OfferLetterFields(**normalized)


if __name__ == "__main__":
    import sys

    # Default test configuration
    TESTS = {
        "i20": ("data/templates/i20.pdf", process_i20),
        "ead": ("data/templates/ead.jpg", process_ead),
        "offer": ("data/templates/OPT_offer_letter_sample.pdf", process_offer_letter),
    }

    # Get document type from command line or default to i20
    doc_type = sys.argv[1] if len(sys.argv) > 1 else "offer"

    if doc_type not in TESTS:
        print(f"Unknown document type: {doc_type}")
        print(f"Available: {', '.join(TESTS.keys())}")
        sys.exit(1)

    file_path, processor = TESTS[doc_type]

    print(f"Processing {doc_type.upper()}: {file_path}")
    print("=" * 50)

    result = processor(file_path)

    print("\n📋 EXTRACTED FIELDS:")
    print("-" * 40)
    for field, value in result.model_dump().items():
        print(f"  {field}: {value}")
