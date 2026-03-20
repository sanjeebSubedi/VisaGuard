# I-20 Few-Shot Prompt and Schema Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the I-20 extraction contract to the full required field set and replace the generic I-20 prompt with a specialized few-shot prompt, while keeping the rest of the Ollama extraction pipeline unchanged.

**Architecture:** Keep the existing Docling -> Ollama -> validation -> snapshot pipeline intact, but update the I-20 prompt file, I-20 response schema, required-field configuration, and related tests. Treat `school_code`, `program_start_date`, and `program_end_date` as optional, while the remaining I-20 fields participate in existing missing-field retry and validation behavior.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic v2, `uv`, `docling`, `ollama`, `pytest`, `httpx`

---

## File Structure

### Planned files and responsibilities

- `app/services/llm/prompts/i20.txt` - replace the generic I-20 prompt with a specialized few-shot prompt tailored for `qwen3:4b-instruct`
- `app/services/llm/schemas.py` - expand `I20ExtractionResult` to include the agreed 10-field contract
- `app/services/llm/prompt_registry.py` - update the I-20 required-field list and bump the I-20 prompt version
- `app/services/validation_rules.py` - ensure optional I-20 fields are not treated as missing-field failures and that any new I-20 date fields use existing date validation behavior only when present
- `tests/unit/test_prompt_registry.py` - verify the updated I-20 required-field split and prompt version
- `tests/unit/test_llm_schemas.py` - verify the expanded I-20 schema parses all target fields and allows `null` for optional ones
- `tests/unit/test_llm_extractor.py` - verify the LLM extraction service can parse the expanded I-20 response shape without disturbing retry behavior
- `tests/integration/test_pipeline.py` - update mocked I-20 extraction to include the expanded field set and verify those values flow into the persisted snapshot/review path
- `tests/conftest.py` - update the integration LLM stub for `i20` only so end-to-end tests reflect the expanded contract

### Data and control boundaries

- Only `i20` changes in this plan; `ead` and `offer_letter` stay untouched
- The Ollama adapter and extraction orchestration remain unchanged unless test evidence proves otherwise
- The required/optional I-20 field split should be defined in `prompt_registry.py` and consumed by validation as the source of truth
- Snapshot assembly should continue consuming facts generically without document-type-specific branching for this slice

### Implementation rules

- Follow strict TDD: failing test first, then minimal implementation, then verification, then commit
- Keep the change isolated to I-20 prompt/schema/config/test files unless a failing test proves another file must change
- Do not change outward API schemas
- Do not change retry counts or introduce new extraction logic in this slice
- Keep prompts compact but specialized enough for a 4B local model

## Task 1: Expand the I-20 Prompt Contract and Required-Field Configuration

**Files:**
- Modify: `app/services/llm/prompts/i20.txt`
- Modify: `app/services/llm/prompt_registry.py`
- Test: `tests/unit/test_prompt_registry.py`

- [ ] **Step 1: Write the failing prompt-registry test**

```python
from app.services.llm.prompt_registry import get_prompt_spec


def test_prompt_registry_returns_expanded_i20_required_fields():
    spec = get_prompt_spec("i20")

    assert spec.prompt_version == "v2"
    assert spec.required_fields == (
        "sevis_id",
        "surname",
        "given_name",
        "cip_code",
        "major",
        "education_level",
        "school_name",
    )
    assert "few-shot" in spec.template.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_prompt_registry.py -v`
Expected: FAIL because the I-20 prompt version and required-field set are still the old contract

- [ ] **Step 3: Write minimal implementation**

Update `app/services/llm/prompts/i20.txt` to include:
- the full I-20 field list
- required vs optional guidance
- normalization instructions
- one or two compact few-shot examples
- strict JSON-only output instruction

Update `app/services/llm/prompt_registry.py`:

```python
PromptSpec(
    document_type="i20",
    template=(PROMPT_DIR / "i20.txt").read_text(),
    prompt_version="v2",
    required_fields=(
        "sevis_id",
        "surname",
        "given_name",
        "cip_code",
        "major",
        "education_level",
        "school_name",
    ),
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_prompt_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/llm/prompts/i20.txt app/services/llm/prompt_registry.py tests/unit/test_prompt_registry.py
git commit -m "feat: expand I-20 prompt contract"
```

## Task 2: Expand the I-20 Response Schema

**Files:**
- Modify: `app/services/llm/schemas.py`
- Test: `tests/unit/test_llm_schemas.py`

- [ ] **Step 1: Write the failing I-20 schema test**

```python
from app.services.llm.schemas import I20ExtractionResult


def test_i20_schema_supports_expanded_field_set():
    result = I20ExtractionResult.model_validate(
        {
            "sevis_id": "N0035706308",
            "surname": "Subedi",
            "given_name": "Sanjeeb",
            "cip_code": "11.0701",
            "major": "Computer Science",
            "education_level": "Master's",
            "school_name": "Example University",
            "school_code": None,
            "program_start_date": None,
            "program_end_date": None,
        }
    )

    assert result.sevis_id == "N0035706308"
    assert result.school_code is None
    assert result.program_end_date is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_llm_schemas.py -v`
Expected: FAIL because `I20ExtractionResult` only supports three fields today

- [ ] **Step 3: Write minimal implementation**

Expand `I20ExtractionResult` in `app/services/llm/schemas.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_llm_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/llm/schemas.py tests/unit/test_llm_schemas.py
git commit -m "feat: expand I-20 extraction schema"
```

## Task 3: Verify Extraction Service Handles the Expanded I-20 Shape

**Files:**
- Modify: `tests/unit/test_llm_extractor.py`
- Possibly modify: `app/services/llm/extractor.py`

- [ ] **Step 1: Write the failing extraction-service test**

```python
from app.services.llm.extractor import LLMExtractionService


def test_llm_extractor_parses_expanded_i20_shape(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm.extractor.OllamaClientAdapter.generate",
        lambda self, **kwargs: '{"sevis_id": "N0035706308", "surname": "Subedi", "given_name": "Sanjeeb", "cip_code": "11.0701", "major": "Computer Science", "education_level": "Master\'s", "school_name": "Example University", "school_code": null, "program_start_date": null, "program_end_date": null}',
    )

    service = LLMExtractionService(model_name="qwen3:4b-instruct")
    result = service.extract(document_type="i20", parsed_text="doc text")

    assert result.values["sevis_id"] == "N0035706308"
    assert result.values["program_end_date"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_llm_extractor.py -v`
Expected: FAIL if the expanded schema shape does not yet flow through the extraction service cleanly

- [ ] **Step 3: Write minimal implementation**

Only change `app/services/llm/extractor.py` if required by the failing test. Prefer no implementation change if the generic schema parsing already supports the expanded I-20 fields.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_llm_extractor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_llm_extractor.py app/services/llm/extractor.py
git commit -m "test: cover expanded I-20 extraction shape"
```

## Task 4: Keep Validation Correct for Required vs Optional I-20 Fields

**Files:**
- Modify: `app/services/validation_rules.py`
- Test: `tests/unit/test_validation_rules.py`

- [ ] **Step 1: Write the failing validation test**

```python
from app.services.validation_rules import validate_extracted_values


def test_validate_extracted_values_allows_missing_optional_i20_fields():
    result = validate_extracted_values(
        document_type="i20",
        values={
            "sevis_id": "N0035706308",
            "surname": "Subedi",
            "given_name": "Sanjeeb",
            "cip_code": "11.0701",
            "major": "Computer Science",
            "education_level": "Master's",
            "school_name": "Example University",
            "school_code": None,
            "program_start_date": None,
            "program_end_date": None,
        },
    )

    assert result.missing_fields == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_validation_rules.py -v`
Expected: FAIL if optional I-20 fields are still treated as required

- [ ] **Step 3: Write minimal implementation**

Keep `validate_extracted_values(...)` driven by `prompt_registry.required_fields` and ensure the expanded I-20 required-field list is the only source of missing-field enforcement. If date validation touches new I-20 optional date fields, keep it format-only when values are present.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_validation_rules.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/validation_rules.py tests/unit/test_validation_rules.py
git commit -m "feat: support optional I-20 fields in validation"
```

## Task 5: Update Integration Stubs and Snapshot Flow for the Expanded I-20 Fields

**Files:**
- Modify: `tests/conftest.py`
- Modify: `tests/integration/test_pipeline.py`

- [ ] **Step 1: Write the failing integration test**

```python
def test_snapshot_contract_includes_expanded_i20_fields(client):
    client.post(
        "/api/intake/documents",
        data={"user_id": "student-1", "document_type": "i20"},
        files={"file": ("i20.pdf", b"pdf", "application/pdf")},
    )

    snapshot = client.get("/api/intake/users/student-1/snapshot")
    body = snapshot.json()

    assert body["snapshot_payload"]["sevis_id"] == "N0035706308"
    assert body["snapshot_payload"]["major"] == "Computer Science"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_pipeline.py -v`
Expected: FAIL because the integration I-20 LLM stub still returns the old smaller field set

- [ ] **Step 3: Write minimal implementation**

Update `tests/conftest.py` so the mocked I-20 LLM extraction returns the expanded I-20 field set:

```python
values = {
    "sevis_id": "N0035706308",
    "surname": "Subedi",
    "given_name": "Sanjeeb",
    "cip_code": "11.0701",
    "major": "Computer Science",
    "education_level": "Master's",
    "school_name": "Example University",
    "school_code": None,
    "program_start_date": None,
    "program_end_date": None,
}
```

Update integration assertions to verify the new fields are present in the snapshot path while leaving `ead` and `offer_letter` expectations stable.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_pipeline.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/integration/test_pipeline.py
git commit -m "test: cover expanded I-20 snapshot fields"
```

## Final Verification Checklist

- [ ] I-20 prompt uses a specialized few-shot structure
- [ ] I-20 prompt version is bumped and tracked in the prompt registry
- [ ] I-20 schema includes all 10 requested fields
- [ ] only the 7 agreed I-20 fields are treated as required
- [ ] `school_code`, `program_start_date`, and `program_end_date` can remain `null`
- [ ] extraction service parses the expanded I-20 JSON shape
- [ ] integration stubs return the expanded I-20 field set
- [ ] snapshot flow can surface new I-20 fields without changing the outward API shape
- [ ] `ead` and `offer_letter` behavior remains unchanged

## Suggested Execution Order

1. Tasks 1-2 to expand the prompt contract and schema
2. Tasks 3-4 to verify extraction/validation behavior remains correct
3. Task 5 to update integration stubs and prove the new I-20 fields flow through the system
