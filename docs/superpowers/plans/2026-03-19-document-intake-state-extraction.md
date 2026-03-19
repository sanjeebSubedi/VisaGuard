# Document Intake and State Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first VisaGuard slice: accept user-labeled `i20`, `ead`, and `offer_letter` uploads, store originals encrypted, parse with `docling`, redact direct identifiers, extract document facts, and assemble a provisional `student_state_snapshot` with review items and eligibility markers.

**Architecture:** This slice is a single FastAPI service with a durable document pipeline. Each document moves through upload, encrypted storage, parse, redaction, extraction, normalization, and snapshot assembly; every stage persists artifacts so failures are retryable and downstream agents can consume only redacted, eligible data.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, SQLite for local/dev tests, `docling`, `cryptography`, `pytest`, `httpx`, `python-multipart`

---

## File Structure

### Planned files and responsibilities

- `pyproject.toml` - project metadata and dependencies
- `.env.example` - local configuration template
- `app/main.py` - FastAPI app bootstrap
- `app/core/config.py` - environment-backed settings
- `app/db/base.py` - SQLAlchemy declarative base
- `app/db/session.py` - engine/session factory
- `app/db/models.py` - `document`, `document_fact`, `review_item`, `student_state_snapshot` models
- `app/api/schemas/intake.py` - request/response models for upload and read APIs
- `app/api/routes/intake.py` - upload and read endpoints
- `app/services/fingerprints.py` - SHA-256 file fingerprinting
- `app/services/crypto.py` - symmetric encryption/decryption for original files
- `app/services/storage.py` - encrypted file storage and artifact persistence
- `app/services/parsing/docling_parser.py` - `docling` adapter + parse result model
- `app/services/redaction.py` - direct-identifier redaction rules
- `app/services/extractors/base.py` - extractor interface and fact model
- `app/services/extractors/i20.py` - `i20` extractor
- `app/services/extractors/ead.py` - `ead` extractor
- `app/services/extractors/offer_letter.py` - `offer_letter` extractor
- `app/services/extractors/router.py` - document-type to extractor routing
- `app/services/normalization.py` - canonical field mapping + precedence rules
- `app/services/review_engine.py` - missing/conflict/low-confidence review items and eligibility rules
- `app/services/pipeline.py` - orchestration for one document through all stages and snapshot refresh
- `tests/conftest.py` - shared fixtures and test app/database setup
- `tests/unit/test_config.py` - settings and bootstrapping tests
- `tests/unit/test_models.py` - persistence model tests
- `tests/unit/test_storage.py` - fingerprint/encryption/storage tests
- `tests/unit/test_docling_parser.py` - parse stage tests using a fake adapter
- `tests/unit/test_redaction.py` - redaction safety tests
- `tests/unit/test_extractors.py` - extractor routing and fact extraction tests
- `tests/unit/test_normalization.py` - precedence, conflicts, and eligibility tests
- `tests/integration/test_intake_api.py` - upload + read API integration tests
- `tests/integration/test_pipeline.py` - durable artifact chain integration tests
- `tests/integration/test_privacy_boundary.py` - downstream-safe response regression tests
- `README.md` - setup and pipeline overview

### Data model boundaries

- `document` owns file metadata, artifact status, and storage locations
- `document_fact` owns candidate facts from a single source document
- `review_item` owns required human follow-up before automated use
- `student_state_snapshot` owns the latest canonical state payload plus provenance and eligibility maps

### Implementation rules

- Keep extractors rule-based in this slice; do not introduce LLM extraction yet
- Keep pipeline synchronous for MVP; do not add a job queue yet
- Use clean readable fixtures only; partial scans are out of scope
- Persist raw parse artifacts and redacted derivatives separately
- Downstream APIs must never return encrypted originals or raw unredacted parse content

## Task 1: Project Scaffold and Runtime Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `app/main.py`
- Create: `app/core/config.py`
- Create: `app/db/base.py`
- Create: `app/db/session.py`
- Create: `tests/conftest.py`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing configuration/bootstrap test**

```python
from app.core.config import Settings


def test_settings_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'visaguard.db'}")
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

    settings = Settings()

    assert settings.database_url.startswith("sqlite:///")
    assert settings.storage_root.endswith("storage")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError` for `app.core.config`

- [ ] **Step 3: Write minimal implementation**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    storage_root: str
    encryption_key: str
```

Also add `FastAPI` app bootstrap and SQLAlchemy base/session wiring so later tasks have a stable import path.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .env.example app/main.py app/core/config.py app/db/base.py app/db/session.py tests/conftest.py tests/unit/test_config.py
git commit -m "chore: scaffold visaguard intake service"
```

## Task 2: Persistence Models for Documents, Facts, Review Items, and Snapshots

**Files:**
- Modify: `app/db/session.py`
- Create: `app/db/models.py`
- Test: `tests/unit/test_models.py`

- [ ] **Step 1: Write the failing persistence test**

```python
from app.db.models import Document, StudentStateSnapshot


def test_document_and_snapshot_tables_create(db_session):
    document = Document(user_id="student-1", document_type="i20", parse_status="pending")
    snapshot = StudentStateSnapshot(user_id="student-1", version=1, snapshot_payload={})
    db_session.add_all([document, snapshot])
    db_session.commit()

    assert document.id is not None
    assert snapshot.id is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_models.py -v`
Expected: FAIL with `ImportError` or missing table/model definitions

- [ ] **Step 3: Write minimal implementation**

```python
class Document(Base):
    __tablename__ = "documents"
    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(String, nullable=False)
    document_type = mapped_column(String, nullable=False)
    encrypted_original_uri = mapped_column(String, nullable=True)
    file_fingerprint = mapped_column(String, nullable=True)
    parse_status = mapped_column(String, default="pending")
    redaction_status = mapped_column(String, default="pending")
    extraction_status = mapped_column(String, default="pending")
```

Add matching models for `DocumentFact`, `ReviewItem`, and `StudentStateSnapshot`, with JSON columns for payload/provenance/eligibility maps.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/db/session.py app/db/models.py tests/unit/test_models.py
git commit -m "feat: add durable intake persistence models"
```

## Task 3: Encrypted Original Storage and File Fingerprinting

**Files:**
- Create: `app/services/fingerprints.py`
- Create: `app/services/crypto.py`
- Create: `app/services/storage.py`
- Test: `tests/unit/test_storage.py`

- [ ] **Step 1: Write the failing storage test**

```python
from app.services.storage import ArtifactStorage


def test_store_original_encrypts_bytes(tmp_path):
    storage = ArtifactStorage(root=tmp_path, encryption_key="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

    location = storage.store_original("user-1", "offer_letter.pdf", b"secret content")
    raw_bytes = (tmp_path / location).read_bytes()

    assert raw_bytes != b"secret content"
    assert storage.load_original(location) == b"secret content"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_storage.py -v`
Expected: FAIL because `ArtifactStorage` is not implemented

- [ ] **Step 3: Write minimal implementation**

```python
import hashlib
from pathlib import Path
from cryptography.fernet import Fernet


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class ArtifactStorage:
    def store_original(self, user_id: str, filename: str, content: bytes) -> str:
        encrypted = self._fernet.encrypt(content)
        path = Path("originals") / user_id / filename
        self.write_bytes(path, encrypted)
        return str(path)
```

Persist originals under `storage/originals/<user_id>/...`, and add helpers for parse/redacted artifact JSON/text writes.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_storage.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/fingerprints.py app/services/crypto.py app/services/storage.py tests/unit/test_storage.py
git commit -m "feat: add encrypted artifact storage"
```

## Task 4: Upload API and Document Record Creation

**Files:**
- Create: `app/api/schemas/intake.py`
- Create: `app/api/routes/intake.py`
- Modify: `app/main.py`
- Modify: `app/db/models.py`
- Test: `tests/integration/test_intake_api.py`

- [ ] **Step 1: Write the failing upload API test**

```python
def test_upload_creates_document_record(client, db_session):
    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "i20"},
        files={"file": ("form-i20.pdf", b"fake pdf bytes", "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["document_type"] == "i20"
    assert body["parse_status"] == "pending"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_intake_api.py::test_upload_creates_document_record -v`
Expected: FAIL with `404 Not Found`

- [ ] **Step 3: Write minimal implementation**

```python
@router.post("/api/intake/documents", status_code=201)
def upload_document(user_id: str = Form(...), document_type: str = Form(...), file: UploadFile = File(...)):
    content = file.file.read()
    fingerprint = sha256_bytes(content)
    original_uri = storage.store_original(user_id, file.filename, content)
    document = Document(
        user_id=user_id,
        document_type=document_type,
        encrypted_original_uri=original_uri,
        file_fingerprint=fingerprint,
        parse_status="pending",
        redaction_status="pending",
        extraction_status="pending",
    )
    session.add(document)
    session.commit()
    return document
```

Validate `document_type` against `i20`, `ead`, and `offer_letter` before writing storage or DB state.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_intake_api.py::test_upload_creates_document_record -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/api/schemas/intake.py app/api/routes/intake.py app/main.py app/db/models.py tests/integration/test_intake_api.py
git commit -m "feat: add document upload endpoint"
```

## Task 5: `docling` Parse Stage with Durable Parse Artifacts

**Files:**
- Create: `app/services/parsing/docling_parser.py`
- Modify: `app/services/storage.py`
- Modify: `app/db/models.py`
- Test: `tests/unit/test_docling_parser.py`

- [ ] **Step 1: Write the failing parse test**

```python
from app.services.parsing.docling_parser import ParsedDocument, parse_with_docling


def test_parse_with_docling_returns_text_and_metadata(monkeypatch):
    monkeypatch.setattr(
        "app.services.parsing.docling_parser._docling_parse",
        lambda _bytes: {"text": "Program Start Date: 2026-08-20", "pages": 1},
    )

    parsed = parse_with_docling(b"pdf bytes")

    assert isinstance(parsed, ParsedDocument)
    assert "Program Start Date" in parsed.text
    assert parsed.metadata["pages"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_docling_parser.py -v`
Expected: FAIL because parse adapter is missing

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass


@dataclass
class ParsedDocument:
    text: str
    metadata: dict
    raw_payload: dict


def parse_with_docling(file_bytes: bytes) -> ParsedDocument:
    payload = _docling_parse(file_bytes)
    return ParsedDocument(text=payload["text"], metadata={"pages": payload.get("pages", 0)}, raw_payload=payload)
```

Add pipeline-ready helpers in storage for saving raw parse JSON under `storage/parsed/`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_docling_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/parsing/docling_parser.py app/services/storage.py app/db/models.py tests/unit/test_docling_parser.py
git commit -m "feat: add durable docling parse stage"
```

## Task 6: Redaction Boundary for Direct Identifiers

**Files:**
- Create: `app/services/redaction.py`
- Modify: `app/services/storage.py`
- Modify: `app/db/models.py`
- Test: `tests/unit/test_redaction.py`

- [ ] **Step 1: Write the failing redaction test**

```python
from app.services.redaction import redact_direct_identifiers


def test_redaction_removes_direct_identifiers_only():
    text = """
    Student Name: Ada Lovelace
    SEVIS ID: N0012345678
    Email: ada@example.com
    Employer: OpenAI
    Start Date: 2026-09-01
    """

    redacted = redact_direct_identifiers(text)

    assert "Ada Lovelace" not in redacted.text
    assert "N0012345678" not in redacted.text
    assert "ada@example.com" not in redacted.text
    assert "OpenAI" in redacted.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_redaction.py -v`
Expected: FAIL because redaction service is missing

- [ ] **Step 3: Write minimal implementation**

```python
import re


@dataclass
class RedactionResult:
    text: str
    replacements: list[dict]


def redact_direct_identifiers(text: str) -> RedactionResult:
    patterns = [
        (r"SEVIS ID:\s*\S+", "SEVIS ID: [REDACTED]"),
        (r"[\w.+-]+@[\w.-]+", "[REDACTED_EMAIL]"),
    ]
    redacted_text = text
    replacements = []
    for pattern, replacement in patterns:
        redacted_text = re.sub(pattern, replacement, redacted_text)
        replacements.append({"pattern": pattern, "replacement": replacement})
    return RedactionResult(text=redacted_text, replacements=replacements)
```

Handle the agreed direct identifiers only: name, SEVIS ID, A-number, DOB, address, phone, email. Save a redacted artifact under `storage/redacted/`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_redaction.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/redaction.py app/services/storage.py app/db/models.py tests/unit/test_redaction.py
git commit -m "feat: add downstream-safe redaction stage"
```

## Task 7: Rule-Based Document Extractors and Routing

**Files:**
- Create: `app/services/extractors/base.py`
- Create: `app/services/extractors/i20.py`
- Create: `app/services/extractors/ead.py`
- Create: `app/services/extractors/offer_letter.py`
- Create: `app/services/extractors/router.py`
- Test: `tests/unit/test_extractors.py`

- [ ] **Step 1: Write the failing extractor routing test**

```python
from app.services.extractors.router import get_extractor


def test_get_extractor_returns_i20_extractor():
    extractor = get_extractor("i20")
    facts = extractor.extract("Program Start Date: 2026-08-20\nCIP Code: 11.0101")

    field_names = {fact.field_name for fact in facts}
    assert "program_start_date" in field_names
    assert "cip_code" in field_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_extractors.py -v`
Expected: FAIL because extractor router is missing

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass
class ExtractedFact:
    field_name: str
    value: str
    confidence: float
    source_location: str
    status: str = "provisional"
```

Implement rule-based extractors:
- `i20`: program dates, CIP code, school name, practical training fields if present
- `ead`: card validity dates, category/class code
- `offer_letter`: employer name, title, start date, compensation if present

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_extractors.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/extractors/base.py app/services/extractors/i20.py app/services/extractors/ead.py app/services/extractors/offer_letter.py app/services/extractors/router.py tests/unit/test_extractors.py
git commit -m "feat: add document-specific extractors"
```

## Task 8: Normalization, Precedence Rules, Review Items, and Snapshot Eligibility

**Files:**
- Create: `app/services/normalization.py`
- Create: `app/services/review_engine.py`
- Modify: `app/db/models.py`
- Test: `tests/unit/test_normalization.py`

- [ ] **Step 1: Write the failing normalization test**

```python
from app.services.normalization import build_snapshot
from app.services.extractors.base import ExtractedFact


def test_build_snapshot_prefers_ead_for_authorization_dates_and_blocks_conflicts():
    facts = [
        ExtractedFact(field_name="employment_authorized_until", value="2027-08-19", confidence=0.98, source_location="ead:1"),
        ExtractedFact(field_name="employment_authorized_until", value="2027-08-01", confidence=0.91, source_location="offer_letter:1"),
    ]

    snapshot = build_snapshot(facts_by_document_type={"ead": [facts[0]], "offer_letter": [facts[1]]})

    assert snapshot.payload["employment_authorized_until"] == "2027-08-19"
    assert snapshot.eligibility_map["employment_authorized_until"] is False
    assert snapshot.review_items[0].review_type == "conflict"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_normalization.py -v`
Expected: FAIL because snapshot builder is missing

- [ ] **Step 3: Write minimal implementation**

```python
PRECEDENCE = {
    "employment_authorization": ["ead", "offer_letter", "i20"],
    "academic_program": ["i20", "ead", "offer_letter"],
    "employment_offer": ["offer_letter", "ead", "i20"],
}
```

Implement `build_snapshot(facts_by_document_type)` to:
- normalize field names/types
- select a precedence winner
- create review items for missing/conflict/low-confidence
- mark unresolved/provisional/conflicted fields as ineligible
- emit provenance for the winning source fact

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_normalization.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/normalization.py app/services/review_engine.py app/db/models.py tests/unit/test_normalization.py
git commit -m "feat: build canonical snapshot and review engine"
```

## Task 9: Pipeline Orchestration and Read APIs

**Files:**
- Create: `app/services/pipeline.py`
- Modify: `app/api/routes/intake.py`
- Modify: `app/api/schemas/intake.py`
- Test: `tests/integration/test_pipeline.py`
- Modify: `tests/integration/test_intake_api.py`

- [ ] **Step 1: Write the failing pipeline integration test**

```python
def test_processing_pipeline_persists_artifacts_and_snapshot(client):
    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "offer_letter"},
        files={"file": ("offer.pdf", OFFER_LETTER_FIXTURE_BYTES, "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["redaction_status"] == "completed"
    assert body["extraction_status"] == "completed"

    snapshot = client.get("/api/intake/users/student-1/snapshot").json()
    assert snapshot["snapshot_payload"]["employer_name"] == "OpenAI"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_pipeline.py -v`
Expected: FAIL because the upload endpoint only creates a pending record

- [ ] **Step 3: Write minimal implementation**

```python
class DocumentPipeline:
    def process_uploaded_document(self, document_id: int) -> Document:
        document = self.repo.get_document(document_id)
        parsed = parse_with_docling(self.storage.load_original(document.encrypted_original_uri))
        redacted = redact_direct_identifiers(parsed.text)
        facts = get_extractor(document.document_type).extract(redacted.text)
        snapshot = build_snapshot({document.document_type: facts})
        self.repo.save_pipeline_outputs(document, parsed, redacted, facts, snapshot)
        updated_document = self.repo.refresh_document(document_id)
        return updated_document
```

Also add read endpoints:
- `GET /api/intake/users/{user_id}/snapshot`
- `GET /api/intake/users/{user_id}/review-items`

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_pipeline.py tests/integration/test_intake_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/pipeline.py app/api/routes/intake.py app/api/schemas/intake.py tests/integration/test_pipeline.py tests/integration/test_intake_api.py
git commit -m "feat: orchestrate intake pipeline and expose snapshot api"
```

## Task 10: End-to-End Hardening, Privacy Regression Tests, and Documentation

**Files:**
- Modify: `tests/integration/test_pipeline.py`
- Create: `tests/integration/test_privacy_boundary.py`
- Modify: `README.md`

- [ ] **Step 1: Write the failing privacy regression test**

```python
def test_snapshot_and_review_endpoints_never_expose_direct_identifiers(client):
    upload_offer_letter_with_email_and_phone(client)

    snapshot = client.get("/api/intake/users/student-1/snapshot").text
    review_items = client.get("/api/intake/users/student-1/review-items").text

    assert "ada@example.com" not in snapshot
    assert "555-111-2222" not in snapshot
    assert "N0012345678" not in review_items
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_privacy_boundary.py -v`
Expected: FAIL if any downstream response still leaks raw identifiers

- [ ] **Step 3: Write minimal implementation**

```python
# Before returning API payloads, use only redacted artifacts and normalized facts.
# Never serialize encrypted originals, raw parse payloads, or redaction replacement maps.
```

Update `README.md` with:
- setup steps
- required env vars
- upload API example
- explanation of restricted vs downstream-safe boundary
- how to run the full test suite

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit -v && pytest tests/integration -v`
Expected: PASS across the full suite

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_pipeline.py tests/integration/test_privacy_boundary.py README.md
git commit -m "docs: finalize intake pipeline and privacy coverage"
```

## Final Verification Checklist

- [ ] `POST /api/intake/documents` stores originals encrypted and persists a document row
- [ ] `docling` parse artifacts are saved separately from redacted artifacts
- [ ] Redaction removes only agreed direct identifiers
- [ ] `i20`, `ead`, and `offer_letter` route to distinct extractors
- [ ] Snapshot precedence matches the spec (`ead` for authorization, `i20` for academic facts, `offer_letter` for employer facts)
- [ ] Missing/conflict/low-confidence fields create `review_item` rows
- [ ] Ineligible fields are visible to humans but blocked for downstream automation
- [ ] Snapshot and review APIs never expose raw unredacted artifacts

## Suggested Execution Order

1. Tasks 1-2 to establish the app shell and persistence contract
2. Tasks 3-6 to build the artifact pipeline up to extracted facts
3. Tasks 7-8 to produce canonical state and reviewability
4. Tasks 9-10 to expose the pipeline through the API and lock in privacy regressions
