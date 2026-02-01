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


# Unified document processor with caching and suto save
def process_document(file_path: str, doc_type: str) -> dict:
    """
    Process a document with cache checking and auto-save.

    Args:
        file_path: Path to the document file
        doc_type: One of "i20", "offer_letter", "ead"

    Returns:
        dict with extracted fields and metadata:
        {
            "cached": bool,  # True if returned from cache
            "id": int,       # Database record ID
            "fields": {...}  # Extracted field values
        }
    """
    from app.db.database import (
        compute_file_hash,
        get_cached_ead,
        get_cached_i20,
        get_cached_offer_letter,
        get_session,
        init_db,
        save_ead,
        save_i20,
        save_offer_letter,
    )

    # Ensure database exists
    init_db()

    # Compute file hash
    file_hash = compute_file_hash(file_path)

    # Check cache
    cache_funcs = {
        "i20": get_cached_i20,
        "offer_letter": get_cached_offer_letter,
        "ead": get_cached_ead,
    }

    with get_session() as session:
        get_cached = cache_funcs.get(doc_type)
        if get_cached:
            cached_doc = get_cached(session, file_hash)
            if cached_doc:
                return {
                    "cached": True,
                    "id": cached_doc.id,
                    "fields": cached_doc.model_dump(
                        exclude={"id", "file_path", "file_hash", "created_at"}
                    ),
                }

    # Not cached - process the document
    process_funcs = {
        "i20": process_i20,
        "offer_letter": process_offer_letter,
        "ead": process_ead,
    }

    processor = process_funcs.get(doc_type)
    if not processor:
        raise ValueError(f"Unknown document type: {doc_type}")

    result = processor(file_path)
    fields = result.model_dump()

    # Save to database
    save_funcs = {
        "i20": save_i20,
        "offer_letter": save_offer_letter,
        "ead": save_ead,
    }

    with get_session() as session:
        save_func = save_funcs[doc_type]
        doc_id = save_func(session, file_path, file_hash, fields)

    return {
        "cached": False,
        "id": doc_id,
        "fields": fields,
    }


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


# I-20 PROCESSOR (Fields Only)

from app.services.prompts import I20_EXTRACTION_PROMPT


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


# EAD PROCESSOR (Fields Only)

from app.services.prompts import EAD_EXTRACTION_PROMPT


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


# OFFER LETTER PROCESSOR (Multi-Call Focused Extraction)

from app.services.prompts import (
    EMPLOYMENT_DETAILS_PROMPT,
    JOB_AND_LOCATION_PROMPT,
    MISSING_FIELDS_RECOVERY_PROMPT,
    SUPERVISOR_PROMPT,
)


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

        missing_fields_str = chr(10).join("- " + f for f in missing_fields)
        recovery_prompt = MISSING_FIELDS_RECOVERY_PROMPT.format(
            missing_fields=missing_fields_str, text=text
        )
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

    # Map short names to doc_type
    DOC_TYPE_MAP = {
        "i20": "i20",
        "ead": "ead",
        "offer": "offer_letter",
    }

    FILES = {
        "i20": "data/templates/i20.pdf",
        "ead": "data/templates/ead.jpg",
        "offer": "data/templates/OPT_offer_letter_sample.pdf",
    }

    # Get document type from command line or default to offer
    arg = sys.argv[1] if len(sys.argv) > 1 else "i20"

    if arg not in DOC_TYPE_MAP:
        print(f"Unknown document type: {arg}")
        print(f"Available: {', '.join(DOC_TYPE_MAP.keys())}")
        sys.exit(1)

    doc_type = DOC_TYPE_MAP[arg]
    file_path = FILES[arg]

    print(f"Processing {arg.upper()}: {file_path}")
    print("=" * 50)

    # Use unified processor with caching
    result = process_document(file_path, doc_type)

    if result["cached"]:
        print("\n⚡ CACHED RESULT (duplicate file detected)")
    else:
        print("\n✨ NEW DOCUMENT PROCESSED")

    print(f"📁 Database ID: {result['id']}")
    print("\n📋 EXTRACTED FIELDS:")
    print("-" * 40)
    for field, value in result["fields"].items():
        print(f"  {field}: {value}")
