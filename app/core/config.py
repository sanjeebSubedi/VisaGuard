import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = (BASE_DIR / "data").resolve()
TEMPLATES_DIR = (DATA_DIR / "templates").resolve()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/visaguard")

PII_ENTITIES_TO_DETECT = [
    # Standard PII
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "US_SSN",
    "US_PASSPORT",
    "CREDIT_CARD",
    # F-1 Specific Entities (custom recognizers)
    "SEVIS_ID",
    "USCIS_CASE_NO",
    "A_NUMBER",
]
