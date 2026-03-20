# Ollama LLM Extraction Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current regex-based document extractors with a synchronous Ollama-backed LLM extraction flow that uses `qwen3:4b-instruct`, keeps deterministic validation after extraction, and preserves the existing outward intake/snapshot API contract.

**Architecture:** Keep Docling as the parse layer and introduce a new LLM extraction subsystem with document-type prompt files, strict JSON response models, a thin Ollama client adapter, one malformed-JSON repair attempt, and one missing-fields retry. Persist normalized facts as before, add raw LLM JSON plus prompt/model metadata for debugging, and keep deterministic validation and snapshot assembly outside the model.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic v2, `uv`, `docling`, `ollama`, `pytest`, `httpx`, `python-multipart`

---

## File Structure

### Planned files and responsibilities

- `pyproject.toml` - add the Ollama Python dependency and keep runtime/dev dependencies current
- `README.md` - document Ollama setup, model pull, local startup, and manual upload workflow
- `app/core/config.py` - add Ollama settings (`OLLAMA_MODEL`, `OLLAMA_HOST`, timeout) with sane defaults
- `app/main.py` - initialize database tables on startup so manual local uploads work without a hidden bootstrap step
- `app/db/models.py` - persist LLM debug metadata such as raw JSON artifact URI, model name, and prompt version
- `app/services/storage.py` - persist raw LLM JSON artifacts using the existing storage abstraction
- `app/services/llm/__init__.py` - package marker for the new LLM extraction subsystem
- `app/services/llm/prompts/i20.txt` - prompt template for I-20 extraction
- `app/services/llm/prompts/ead.txt` - prompt template for EAD extraction
- `app/services/llm/prompts/offer_letter.txt` - prompt template for offer-letter extraction
- `app/services/llm/prompt_registry.py` - load prompt files, expose prompt versions, and declare per-document required fields
- `app/services/llm/schemas.py` - Pydantic response models for `i20`, `ead`, and `offer_letter`
- `app/services/llm/ollama_client.py` - thin adapter around the Ollama Python client with timeout/unavailable handling
- `app/services/llm/extractor.py` - orchestrate first-pass extraction, JSON repair, missing-fields retry, and fact conversion
- `app/services/validation_rules.py` - deterministic post-extraction validation for missing required fields and simple format checks
- `app/services/pipeline.py` - swap regex extractor routing for the new LLM extraction flow and persist LLM debug artifacts
- `app/services/extractors/router.py` - remove document-type regex routing or replace it with a minimal compatibility shim if still needed
- `tests/conftest.py` - add shared Ollama stubs and keep Docling stubbing in place for fast deterministic tests
- `tests/unit/test_config.py` - cover new Ollama settings defaults/overrides
- `tests/unit/test_models.py` - cover new LLM debug metadata persistence fields
- `tests/unit/test_storage.py` - cover persisted LLM JSON artifact writes
- `tests/unit/test_prompt_registry.py` - cover prompt loading, versioning, and required-field lookups
- `tests/unit/test_ollama_client.py` - cover successful calls and unavailable-service failures
- `tests/unit/test_llm_schemas.py` - cover strict JSON parsing and `null` handling for each document type
- `tests/unit/test_llm_extractor.py` - cover first-pass success, malformed-JSON repair, and missing-fields retry
- `tests/unit/test_validation_rules.py` - cover deterministic missing-field/date validation after LLM extraction
- `tests/integration/test_intake_api.py` - cover synchronous upload success and hard failure when Ollama is unavailable
- `tests/integration/test_pipeline.py` - cover end-to-end persistence, raw LLM JSON retention, and snapshot stability under mocked Ollama output
- `tests/integration/test_privacy_boundary.py` - ensure API responses still do not leak storage URIs or debug artifacts

### Data and control boundaries

- `app/services/parsing/docling_parser.py` remains the only Docling integration point
- `app/services/llm/ollama_client.py` is the only place that should know the Ollama Python client API
- `app/services/llm/extractor.py` owns LLM orchestration and should not contain downstream compliance logic
- `app/services/validation_rules.py` owns deterministic post-extraction checks
- `app/services/pipeline.py` owns document lifecycle transitions and artifact persistence
- outward API schemas remain intentionally unchanged

### Implementation rules

- Use TDD for every behavior change: write failing test, run it, implement minimally, rerun, commit
- Keep extraction synchronous in the upload request
- Use one configured model only: `qwen3:4b-instruct`
- Use strict JSON only; do not add free-form parsing heuristics beyond one repair attempt
- Retry exactly once for malformed JSON and exactly once for missing required fields
- Persist `null` for still-missing fields after the second pass
- Keep deterministic validators for required fields, date formats, cross-document conflicts, and eligibility
- Do not expose raw LLM JSON or artifact URIs in outward API responses

## Task 1: Add Ollama Configuration and Prompt Registry Skeleton

**Files:**
- Modify: `pyproject.toml`
- Modify: `app/core/config.py`
- Create: `app/services/llm/__init__.py`
- Create: `app/services/llm/prompts/i20.txt`
- Create: `app/services/llm/prompts/ead.txt`
- Create: `app/services/llm/prompts/offer_letter.txt`
- Create: `app/services/llm/prompt_registry.py`
- Test: `tests/unit/test_config.py`
- Test: `tests/unit/test_prompt_registry.py`

- [ ] **Step 1: Write the failing config and prompt-registry tests**

```python
from app.core.config import Settings
from app.services.llm.prompt_registry import get_prompt_spec


def test_settings_default_ollama_model(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    settings = Settings()
    assert settings.ollama_model == "qwen3:4b-instruct"


def test_prompt_registry_returns_i20_prompt_spec():
    spec = get_prompt_spec("i20")
    assert spec.prompt_version == "v1"
    assert "program_start_date" in spec.required_fields
    assert "strict JSON" in spec.template
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_config.py tests/unit/test_prompt_registry.py -v`
Expected: FAIL because Ollama settings and prompt registry do not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
class Settings(BaseSettings):
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b-instruct"
    ollama_timeout_seconds: int = 60
```

```python
@dataclass(frozen=True)
class PromptSpec:
    document_type: str
    template: str
    prompt_version: str
    required_fields: tuple[str, ...]
```

Create compact prompt files for `i20`, `ead`, and `offer_letter` and load them from `prompt_registry.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_config.py tests/unit/test_prompt_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml app/core/config.py app/services/llm/__init__.py app/services/llm/prompts/i20.txt app/services/llm/prompts/ead.txt app/services/llm/prompts/offer_letter.txt app/services/llm/prompt_registry.py tests/unit/test_config.py tests/unit/test_prompt_registry.py
git commit -m "feat: add Ollama config and prompt registry"
```

## Task 2: Add the Ollama Client Adapter

**Files:**
- Modify: `pyproject.toml`
- Create: `app/services/llm/ollama_client.py`
- Test: `tests/unit/test_ollama_client.py`

- [ ] **Step 1: Write the failing Ollama adapter tests**

```python
import pytest

from app.services.llm.ollama_client import OllamaClientAdapter, OllamaUnavailableError


def test_ollama_client_returns_response_text(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm.ollama_client.Client",
        lambda host=None, timeout=None: type("FakeClient", (), {
            "generate": lambda self, model, prompt, options=None: {"response": '{"program_start_date": "2026-08-20"}'}
        })(),
    )

    adapter = OllamaClientAdapter(host="http://127.0.0.1:11434", timeout_seconds=30)

    assert adapter.generate(model="qwen3:4b-instruct", prompt="extract") == '{"program_start_date": "2026-08-20"}'


def test_ollama_client_raises_unavailable_error(monkeypatch):
    def fake_client(*args, **kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr("app.services.llm.ollama_client.Client", fake_client)

    with pytest.raises(OllamaUnavailableError):
        OllamaClientAdapter(host="http://127.0.0.1:11434", timeout_seconds=30)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_ollama_client.py -v`
Expected: FAIL because the adapter does not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
class OllamaUnavailableError(RuntimeError):
    pass


class OllamaClientAdapter:
    def __init__(self, host: str, timeout_seconds: int) -> None:
        try:
            self._client = Client(host=host, timeout=timeout_seconds)
        except Exception as exc:
            raise OllamaUnavailableError(str(exc)) from exc

    def generate(self, *, model: str, prompt: str) -> str:
        try:
            response = self._client.generate(model=model, prompt=prompt)
        except Exception as exc:
            raise OllamaUnavailableError(str(exc)) from exc
        return response["response"]
```

Add `ollama` to `pyproject.toml` via `uv`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_ollama_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock app/services/llm/ollama_client.py tests/unit/test_ollama_client.py
git commit -m "feat: add Ollama client adapter"
```

## Task 3: Add LLM Response Schemas and Extraction Orchestration

**Files:**
- Create: `app/services/llm/schemas.py`
- Create: `app/services/llm/extractor.py`
- Test: `tests/unit/test_llm_schemas.py`
- Test: `tests/unit/test_llm_extractor.py`

- [ ] **Step 1: Write the failing schema and extractor tests**

```python
from app.services.llm.extractor import LLMExtractionService
from app.services.llm.schemas import I20ExtractionResult


def test_i20_schema_accepts_null_optional_fields():
    result = I20ExtractionResult.model_validate({
        "program_start_date": "2026-08-20",
        "cip_code": None,
        "school_name": "Example University",
    })
    assert result.cip_code is None


def test_llm_extractor_repairs_json_and_retries_missing_fields(monkeypatch):
    responses = iter([
        '{"program_start_date": "2026-08-20"',
        '{"program_start_date": null, "cip_code": null, "school_name": "Example University"}',
        '{"program_start_date": "2026-08-20", "cip_code": "11.0701"}',
    ])

    monkeypatch.setattr(
        "app.services.llm.extractor.OllamaClientAdapter.generate",
        lambda self, **kwargs: next(responses),
    )

    service = LLMExtractionService(model_name="qwen3:4b-instruct")
    result = service.extract(document_type="i20", parsed_text="doc text")

    assert result.values["program_start_date"] == "2026-08-20"
    assert result.values["cip_code"] == "11.0701"
    assert result.prompt_version == "v1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_llm_schemas.py tests/unit/test_llm_extractor.py -v`
Expected: FAIL because schemas and extractor orchestration do not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
class I20ExtractionResult(BaseModel):
    program_start_date: str | None
    cip_code: str | None
    school_name: str | None
```

```python
@dataclass
class LLMExtractionOutcome:
    values: dict[str, str | None]
    raw_json: dict
    prompt_version: str
    model_name: str
```

Implement `LLMExtractionService.extract(...)` to:
- load the document prompt
- call the Ollama adapter
- parse strict JSON
- do one JSON repair attempt if parsing fails
- do one missing-fields retry if required fields are `None`
- merge missing-field retry results into the original values

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_llm_schemas.py tests/unit/test_llm_extractor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/llm/schemas.py app/services/llm/extractor.py tests/unit/test_llm_schemas.py tests/unit/test_llm_extractor.py
git commit -m "feat: add LLM extraction service"
```

## Task 4: Persist LLM Debug Artifacts and Metadata

**Files:**
- Modify: `app/db/models.py`
- Modify: `app/services/storage.py`
- Modify: `tests/unit/test_models.py`
- Modify: `tests/unit/test_storage.py`

- [ ] **Step 1: Write the failing persistence tests**

```python
from app.db.models import Document


def test_document_can_track_llm_debug_metadata(db_session):
    document = Document(
        user_id="student-1",
        document_type="i20",
        llm_model_name="qwen3:4b-instruct",
        llm_prompt_version="v1",
        llm_raw_response_uri="llm/document-1.json",
    )
    db_session.add(document)
    db_session.commit()

    assert document.id is not None
    assert document.llm_model_name == "qwen3:4b-instruct"
```

```python
def test_write_llm_response_persists_json(tmp_path):
    storage = ArtifactStorage(root=tmp_path, encryption_key="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
    location = storage.write_llm_response(7, {"program_start_date": "2026-08-20"})
    assert (tmp_path / location).exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_models.py tests/unit/test_storage.py -v`
Expected: FAIL because LLM debug fields and storage helper do not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
class Document(Base):
    llm_model_name: Mapped[str | None] = mapped_column(String, nullable=True)
    llm_prompt_version: Mapped[str | None] = mapped_column(String, nullable=True)
    llm_raw_response_uri: Mapped[str | None] = mapped_column(String, nullable=True)
```

```python
def write_llm_response(self, document_id: int, payload: dict) -> str:
    relative_path = Path("llm") / f"document-{document_id}.json"
    self.write_json(relative_path, payload)
    return str(relative_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_models.py tests/unit/test_storage.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/db/models.py app/services/storage.py tests/unit/test_models.py tests/unit/test_storage.py
git commit -m "feat: persist LLM extraction debug metadata"
```

## Task 5: Add Deterministic Post-Extraction Validators

**Files:**
- Create: `app/services/validation_rules.py`
- Test: `tests/unit/test_validation_rules.py`

- [ ] **Step 1: Write the failing validator tests**

```python
from app.services.validation_rules import validate_extracted_values


def test_validate_extracted_values_marks_missing_required_fields():
    result = validate_extracted_values(
        document_type="ead",
        values={"employment_authorized_until": None, "ead_category": "C03B"},
    )
    assert "employment_authorized_until" in result.missing_fields


def test_validate_extracted_values_rejects_bad_date_format():
    result = validate_extracted_values(
        document_type="offer_letter",
        values={"employment_start_date": "April 27, 2026", "job_title": "Backend Software Engineer", "employer_name": "TechNova"},
    )
    assert "employment_start_date" in result.invalid_fields
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_validation_rules.py -v`
Expected: FAIL because deterministic validation rules do not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass
class ValidationResult:
    missing_fields: list[str]
    invalid_fields: list[str]
```

Implement required-field and ISO-date checks per document type. Keep the implementation intentionally small and leave cross-document conflict handling in the existing snapshot builder.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_validation_rules.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/validation_rules.py tests/unit/test_validation_rules.py
git commit -m "feat: add post-extraction validators"
```

## Task 6: Replace Regex Extraction in the Pipeline with LLM Extraction

**Files:**
- Modify: `app/services/pipeline.py`
- Modify: `app/services/extractors/router.py`
- Modify: `tests/conftest.py`
- Modify: `tests/integration/test_intake_api.py`
- Modify: `tests/integration/test_pipeline.py`
- Modify: `tests/integration/test_privacy_boundary.py`

- [ ] **Step 1: Write the failing integration tests**

```python
def test_upload_fails_when_ollama_is_unavailable(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.pipeline.LLMExtractionService.extract",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("ollama unavailable")),
    )

    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "i20"},
        files={"file": ("i20.pdf", b"pdf", "application/pdf")},
    )

    assert response.status_code == 500
```

```python
def test_offer_letter_upload_persists_llm_artifact_and_redacted_retained_text(client):
    response = client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "offer_letter"},
        files={"file": ("offer.pdf", b"pdf", "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["extraction_status"] == "completed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_intake_api.py tests/integration/test_pipeline.py tests/integration/test_privacy_boundary.py -v`
Expected: FAIL because the pipeline still uses regex extractors and does not persist LLM artifacts

- [ ] **Step 3: Write minimal implementation**

```python
outcome = self.llm_extractor.extract(document_type=document.document_type, parsed_text=parsed.text)
validation = validate_extracted_values(document_type=document.document_type, values=outcome.values)
document.llm_model_name = outcome.model_name
document.llm_prompt_version = outcome.prompt_version
document.llm_raw_response_uri = self.storage.write_llm_response(document.id, outcome.raw_json)
```

Convert non-`None` extracted values into `DocumentFact` rows, set `source_location` to a stable LLM-specific value such as `llm:<field_name>`, and create review items for missing/invalid fields through the validation layer plus snapshot logic. Remove or bypass the old regex routing path.

Update `tests/conftest.py` so integration tests mock the new `LLMExtractionService` while keeping real Docling out of the fast test path.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_intake_api.py tests/integration/test_pipeline.py tests/integration/test_privacy_boundary.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/pipeline.py app/services/extractors/router.py tests/conftest.py tests/integration/test_intake_api.py tests/integration/test_pipeline.py tests/integration/test_privacy_boundary.py
git commit -m "feat: switch intake pipeline to LLM extraction"
```

## Task 7: Keep Snapshot and Review Behavior Stable While Surfacing Missing Fields

**Files:**
- Modify: `app/services/normalization.py`
- Modify: `app/services/review_engine.py`
- Modify: `tests/unit/test_normalization.py`
- Modify: `tests/integration/test_pipeline.py`

- [ ] **Step 1: Write the failing regression tests**

```python
def test_build_snapshot_adds_missing_field_review_items_from_validation_results():
    result = build_snapshot(
        facts_by_document_type={"offer_letter": []},
        validation_results={"offer_letter": {"missing_fields": ["employment_start_date"], "invalid_fields": []}},
    )
    assert any(item.review_type == "missing_field" and item.field_name == "employment_start_date" for item in result.review_items)
```

```python
def test_snapshot_contract_still_returns_expected_fields_after_llm_upgrade(client):
    # upload mocked i20 + ead + offer_letter
    snapshot = client.get("/api/intake/users/student-1/snapshot")
    assert snapshot.status_code == 200
    body = snapshot.json()
    assert body["snapshot_payload"]["program_start_date"] == "2026-08-20"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_normalization.py tests/integration/test_pipeline.py -v`
Expected: FAIL because snapshot assembly does not yet accept validation-driven missing-field items

- [ ] **Step 3: Write minimal implementation**

Extend `build_snapshot(...)` so it can merge deterministic validation results into `review_items` without changing the outward snapshot shape. Keep precedence and eligibility logic intact.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_normalization.py tests/integration/test_pipeline.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/normalization.py app/services/review_engine.py tests/unit/test_normalization.py tests/integration/test_pipeline.py
git commit -m "feat: surface validation-driven review items"
```

## Task 8: Make Local Manual Testing Reliable and Documented

**Files:**
- Modify: `app/main.py`
- Modify: `README.md`
- Test: `tests/integration/test_intake_api.py`

- [ ] **Step 1: Write the failing startup/manual-testing regression test**

```python
def test_app_startup_creates_tables_for_manual_local_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'manual.db'}")
    from app.main import app
    assert app is not None
```

Add an integration assertion that a clean manual app boot no longer requires a hidden database bootstrap command before upload works.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_intake_api.py -v`
Expected: FAIL because local startup currently does not initialize tables automatically

- [ ] **Step 3: Write minimal implementation**

Initialize tables during application startup and update `README.md` with:
- how to start Ollama locally
- how to pull `qwen3:4b-instruct`
- how to start the API with `uv`
- example upload commands for `i20`, `ead`, and `offer_letter`
- how to inspect snapshot and review items

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_intake_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/main.py README.md tests/integration/test_intake_api.py
git commit -m "docs: support manual Ollama-backed intake testing"
```

## Final Verification Checklist

- [ ] `qwen3:4b-instruct` is the configured extraction model
- [ ] each document type uses its own prompt file
- [ ] LLM output is strict JSON only
- [ ] malformed JSON gets one repair attempt only
- [ ] missing required fields get one retry only
- [ ] still-missing fields persist as `null`
- [ ] Ollama unavailability fails the upload request immediately
- [ ] normalized facts still persist and feed snapshot generation
- [ ] raw LLM JSON plus model/prompt metadata persist for debugging
- [ ] retained redacted `offer_letter` text behavior still works
- [ ] snapshot and review-item APIs keep their existing outward contract
- [ ] local manual testing works with a clean app startup and documented Ollama setup

## Suggested Execution Order

1. Tasks 1-2 to add configuration, prompts, and the Ollama adapter boundary
2. Tasks 3-5 to implement extraction orchestration, persistence, and deterministic validation
3. Tasks 6-8 to switch the pipeline, keep snapshot behavior stable, and finish manual-testing support
