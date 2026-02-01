"""
LLM prompts for document field extraction.

Each prompt is specialized for a specific document type or extraction task.
"""

# =============================================================================
# I-20 PROMPTS
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


# =============================================================================
# EAD PROMPTS
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


# =============================================================================
# OFFER LETTER PROMPTS
# =============================================================================

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

MISSING_FIELDS_RECOVERY_PROMPT = """The following fields were NOT found in the first extraction pass.
Search the document VERY CAREFULLY to find them:

Missing fields:
{missing_fields}

Search hints:
- EIN: Look for "Employer Identification Number", "EIN:", or "Tax ID:" followed by XX-XXXXXXX format
- end_date: Look for "End Date:", "Employment ends", or date after "through"
- supervisor: Look in "Supervision" section, "Reports to", or letter signatory

Document:
{text}
"""
