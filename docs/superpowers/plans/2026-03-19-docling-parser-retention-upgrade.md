# Docling Parser and Retention Policy Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current parser stub with real Docling-backed parsing, enforce document-type-specific file validation, and apply policy-driven retention so `i20` and `ead` persist facts only while `offer_letter` persists facts plus full redacted retained text.

**Architecture:** Keep the existing intake/snapshot API stable while introducing an internal document policy layer. The upload route validates file type by declared document type, the Docling adapter handles PDF and image inputs, and the pipeline persists encrypted originals for all uploads but only stores retained redacted text for `offer_letter`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic v2, `uv`, `docling`, `python-multipart`, `pytest`, `httpx`, `cryptography`

---

## File Structure

### Planned files and responsibilities

- `pyproject.toml` - add Docling dependency and keep runtime/dev dependencies current
- `README.md` - update setup and testing notes for real Docling parsing and file-type rules
- `app/api/routes/intake.py` - enforce document-type-specific upload validation and keep API responses stable
- `app/api/schemas/intake.py` - extend/adjust response models if parse failure or retained text metadata needs surfacing internally
- `app/db/models.py` - track parse failures and retained offer-letter text location without exposing raw storage paths externally
- `app/services/parsing/docling_parser.py` - replace stub parser with real Docling adapter for PDFs and images
- `app/services/policy.py` - define document-type-specific validation and retention policy
- `app/services/validation.py` - MIME/extension validation helpers used by upload policy
- `app/services/pipeline.py` - apply policy-driven parse/extract/retain behavior and explicit `parse_failed` handling
- `app/services/storage.py` - persist retained redacted offer-letter text and avoid persisting parser text for `i20`/`ead`
- `app/services/redaction.py` - keep direct-identifier redaction focused on retained `offer_letter` text
- `tests/conftest.py` - shared fixtures for Docling stubbing and temporary storage overrides
- `tests/unit/test_validation.py` - upload file-type validation tests
- `tests/unit/test_docling_parser.py` - Docling adapter tests for PDF/image success and failure
- `tests/unit/test_policy.py` - policy rules for allowed formats and retention behavior
- `tests/integration/test_intake_api.py` - upload validation and parse-failed API behavior
- `tests/integration/test_pipeline.py` - end-to-end persistence behavior by document type
- `tests/integration/test_privacy_boundary.py` - retained-text privacy regression tests

### Data and control boundaries

- `policy.py` is the source of truth for per-document behavior; route and pipeline code should consult policy rather than hardcode conditions repeatedly
- `docling_parser.py` is the only place that should know how to invoke Docling
- `pipeline.py` owns orchestration and status transitions (`pending`, `completed`, `parse_failed`, extraction failures)
- `storage.py` owns artifact persistence; only `offer_letter` retained text is stored downstream

### Implementation rules

- Keep the outward `student_state_snapshot` and review-item endpoints unchanged
- Do not add a secondary OCR/parser fallback in this slice
- Reject invalid type/file combinations before parsing starts
- Persist encrypted originals for all document types
- Persist retained parser text only for `offer_letter`, and only after redaction
- Do not expose storage URIs for encrypted originals or retained text in downstream-safe API responses

## Task 1: Add Policy and Validation Primitives

**Files:**
- Create: `app/services/policy.py`
- Create: `app/services/validation.py`
- Test: `tests/unit/test_policy.py`
- Test: `tests/unit/test_validation.py`

- [ ] **Step 1: Write the failing policy and validation tests**

```python
from app.services.policy import get_document_policy
from app.services.validation import validate_upload


def test_offer_letter_policy_requires_retained_redacted_text():
    policy = get_document_policy("offer_letter")
    assert policy.allowed_kind == "pdf"
    assert policy.persist_retained_text is True
    assert policy.redact_retained_text is True


def test_validate_upload_rejects_pdf_for_ead():
    validate_upload(document_type="ead", filename="card.pdf", content_type="application/pdf")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_policy.py tests/unit/test_validation.py -v`
Expected: FAIL with missing `policy` / `validation` modules

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentPolicy:
    document_type: str
    allowed_kind: str
    persist_retained_text: bool
    redact_retained_text: bool


POLICIES = {
    "i20": DocumentPolicy("i20", "pdf", False, False),
    "ead": DocumentPolicy("ead", "image", False, False),
    "offer_letter": DocumentPolicy("offer_letter", "pdf", True, True),
}
```

Implement `validate_upload(...)` so it checks both filename extension and MIME type and raises a clear validation exception on mismatch.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_policy.py tests/unit/test_validation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/policy.py app/services/validation.py tests/unit/test_policy.py tests/unit/test_validation.py
git commit -m "feat: add document policy and upload validation"
```

## Task 2: Integrate Real Docling for PDF and Image Parsing

**Files:**
- Modify: `pyproject.toml`
- Modify: `app/services/parsing/docling_parser.py`
- Test: `tests/unit/test_docling_parser.py`

- [ ] **Step 1: Write the failing Docling adapter tests**

```python
from app.services.parsing.docling_parser import ParsedDocument, parse_with_docling


def test_parse_with_docling_uses_pdf_input(monkeypatch):
    monkeypatch.setattr(
        "app.services.parsing.docling_parser._convert_with_docling",
        lambda *, file_bytes, filename, content_type: {"text": "Program Start Date: 2026-08-20", "pages": 1},
    )

    parsed = parse_with_docling(file_bytes=b"pdf-bytes", filename="i20.pdf", content_type="application/pdf")

    assert isinstance(parsed, ParsedDocument)
    assert parsed.metadata["pages"] == 1


def test_parse_with_docling_raises_parse_error(monkeypatch):
    monkeypatch.setattr(
        "app.services.parsing.docling_parser._convert_with_docling",
        lambda **_: (_ for _ in ()).throw(RuntimeError("docling failed")),
    )

    parse_with_docling(file_bytes=b"img", filename="ead.png", content_type="image/png")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_docling_parser.py -v`
Expected: FAIL because the current stub parser signature/behavior does not support real Docling invocation

- [ ] **Step 3: Write minimal implementation**

```python
class DoclingParseError(Exception):
    pass


def parse_with_docling(*, file_bytes: bytes, filename: str, content_type: str) -> ParsedDocument:
    try:
        payload = _convert_with_docling(file_bytes=file_bytes, filename=filename, content_type=content_type)
    except Exception as exc:
        raise DoclingParseError(str(exc)) from exc
    return ParsedDocument(text=payload["text"], metadata=payload["metadata"], raw_payload={})
```

Add the real `docling` dependency with `uv`, and implement `_convert_with_docling(...)` using Docling’s current converter API for PDF and image inputs.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_docling_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock app/services/parsing/docling_parser.py tests/unit/test_docling_parser.py
git commit -m "feat: integrate docling parser adapter"
```

## Task 3: Extend Persistence for Parse Failure and Retained Offer-Letter Text

**Files:**
- Modify: `app/db/models.py`
- Modify: `tests/unit/test_models.py`

- [ ] **Step 1: Write the failing persistence test**

```python
from app.db.models import Document


def test_document_can_track_parse_failure_and_retained_text_path(db_session):
    document = Document(
        user_id="student-1",
        document_type="offer_letter",
        parse_status="parse_failed",
        retained_text_uri="retained/offer-letter.txt",
    )
    db_session.add(document)
    db_session.commit()

    assert document.id is not None
    assert document.parse_status == "parse_failed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_models.py -v`
Expected: FAIL because retained-text persistence fields are missing

- [ ] **Step 3: Write minimal implementation**

```python
class Document(Base):
    retained_text_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    parse_error_message: Mapped[str | None] = mapped_column(String, nullable=True)
```

Keep encrypted original location private to internal code; do not add it to outward response models.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/db/models.py tests/unit/test_models.py
git commit -m "feat: track parse failures and retained text metadata"
```

## Task 4: Apply Upload Validation in the API Layer

**Files:**
- Modify: `app/api/routes/intake.py`
- Modify: `tests/integration/test_intake_api.py`

- [ ] **Step 1: Write the failing validation integration tests**

```python
def test_upload_rejects_pdf_for_ead(client):
    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "ead"},
        files={"file": ("ead.pdf", b"fake", "application/pdf")},
    )

    assert response.status_code == 400


def test_upload_accepts_png_for_ead(client):
    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "ead"},
        files={"file": ("ead.png", b"image-bytes", "image/png")},
    )

    assert response.status_code == 201
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_intake_api.py -v`
Expected: FAIL because the current route allows mismatched file kinds

- [ ] **Step 3: Write minimal implementation**

```python
validate_upload(
    document_type=document_type,
    filename=file.filename or "upload.bin",
    content_type=file.content_type or "application/octet-stream",
)
```

Return a clear `400` response on validation failure before storing the original.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_intake_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/api/routes/intake.py tests/integration/test_intake_api.py
git commit -m "feat: enforce upload validation by document type"
```

## Task 5: Make the Pipeline Policy-Driven and Parse-Failure Aware

**Files:**
- Modify: `app/services/pipeline.py`
- Modify: `app/api/routes/intake.py`
- Test: `tests/integration/test_pipeline.py`

- [ ] **Step 1: Write the failing parse-failed integration test**

```python
def test_parse_failure_marks_document_parse_failed(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.pipeline.parse_with_docling",
        lambda **_: (_ for _ in ()).throw(Exception("parse boom")),
    )

    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "i20"},
        files={"file": ("i20.pdf", b"fake-pdf", "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["parse_status"] == "parse_failed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_pipeline.py -v`
Expected: FAIL because parse failures are not yet handled explicitly

- [ ] **Step 3: Write minimal implementation**

```python
policy = get_document_policy(document.document_type)
try:
    parsed = parse_with_docling(...)
except DoclingParseError as exc:
    document.parse_status = "parse_failed"
    document.parse_error_message = str(exc)
    self.session.commit()
    self.session.refresh(document)
    return document
```

Keep extraction/snapshot updates from running after parse failure.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_pipeline.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/pipeline.py app/api/routes/intake.py tests/integration/test_pipeline.py
git commit -m "feat: handle parse failures in intake pipeline"
```

## Task 6: Apply Policy-Driven Retention Behavior

**Files:**
- Modify: `app/services/pipeline.py`
- Modify: `app/services/storage.py`
- Modify: `tests/integration/test_pipeline.py`
- Modify: `tests/integration/test_privacy_boundary.py`

- [ ] **Step 1: Write the failing retention integration tests**

```python
def test_i20_persists_facts_only_without_retained_text(client):
    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "i20"},
        files={"file": ("i20.pdf", I20_FIXTURE_BYTES, "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["parse_status"] == "completed"
    assert retained_text_file_count() == 0


def test_offer_letter_persists_redacted_retained_text(client):
    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "offer_letter"},
        files={"file": ("offer.pdf", OFFER_LETTER_WITH_EMAIL_BYTES, "application/pdf")},
    )

    assert response.status_code == 201
    assert retained_text_contains("[REDACTED_EMAIL]")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_pipeline.py tests/integration/test_privacy_boundary.py -v`
Expected: FAIL because the current pipeline stores redacted text generically rather than policy-driven retained text

- [ ] **Step 3: Write minimal implementation**

```python
if policy.persist_retained_text:
    redacted = redact_direct_identifiers(parsed.text)
    retained_text_uri = Path("retained") / f"document-{document.id}.txt"
    self.storage.write_text(retained_text_uri, redacted.text)
    document.retained_text_uri = str(retained_text_uri)
else:
    document.retained_text_uri = None
```

Do not persist parser text for `i20` or `ead`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_pipeline.py tests/integration/test_privacy_boundary.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/pipeline.py app/services/storage.py tests/integration/test_pipeline.py tests/integration/test_privacy_boundary.py
git commit -m "feat: apply policy-driven document retention"
```

## Task 7: Keep the Snapshot Contract Stable While Updating Fixtures and Docs

**Files:**
- Modify: `README.md`
- Modify: `tests/integration/test_pipeline.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Write the failing regression test for stable outward behavior**

```python
def test_snapshot_contract_still_returns_canonical_fields_after_docling_upgrade(client):
    upload_i20_pdf(client)
    upload_ead_image(client)
    upload_offer_letter_pdf(client)

    snapshot = client.get("/api/intake/users/student-1/snapshot")

    assert snapshot.status_code == 200
    body = snapshot.json()
    assert body["snapshot_payload"]["program_start_date"] == "2026-08-20"
    assert body["snapshot_payload"]["employment_authorized_until"] == "2027-08-19"
    assert body["snapshot_payload"]["employer_name"] == "OpenAI"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_pipeline.py -v`
Expected: FAIL if fixture setup or pipeline behavior drifted during parser/retention changes

- [ ] **Step 3: Write minimal implementation**

```python
# Update test fixtures/stubs so PDF and image uploads both exercise the new parser boundary,
# while keeping the snapshot output shape exactly the same.
```

Update `README.md` with:
- supported file kinds by document type
- real Docling requirement
- note that `offer_letter` retains redacted text while `i20` and `ead` do not
- how to run the full suite with `uv`

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit -v && uv run pytest tests/integration -v`
Expected: PASS across the full suite

- [ ] **Step 5: Commit**

```bash
git add README.md tests/conftest.py tests/integration/test_pipeline.py
git commit -m "docs: finalize docling parser upgrade coverage"
```

## Final Verification Checklist

- [ ] `i20` uploads require PDF and persist facts only
- [ ] `ead` uploads require image input and persist facts only
- [ ] `offer_letter` uploads require PDF and persist facts plus full redacted retained text
- [ ] encrypted originals are still stored for all document types
- [ ] Docling parser handles both PDF and image inputs through one adapter
- [ ] parse failures become `parse_failed` without running extraction/snapshot updates
- [ ] snapshot and review-item endpoints keep their existing outward contract
- [ ] downstream-safe API responses do not expose encrypted original or retained-text storage URIs

## Suggested Execution Order

1. Tasks 1-2 to define policy and replace the parser stub
2. Tasks 3-5 to make persistence and pipeline state transitions production-safe
3. Tasks 6-7 to lock in retention/privacy behavior and re-verify the outward contract
