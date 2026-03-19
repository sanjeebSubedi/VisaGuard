# VisaGuard

VisaGuard is a FastAPI service for the first F-1 compliance slice: document intake and state extraction.

## What this slice does

- accepts user-labeled `i20`, `ead`, and `offer_letter` uploads
- stores original files encrypted on disk
- parses uploads through a `docling` adapter boundary
- redacts direct identifiers before downstream processing
- extracts rule-based document facts
- builds a `student_state_snapshot` with eligibility and review metadata

## Privacy boundaries

### Restricted boundary

- encrypted originals
- raw parse artifacts

### Downstream-safe boundary

- redacted text artifacts
- extracted facts
- review items
- state snapshots

The API never returns encrypted original locations or raw parse payloads.

## Local setup

```bash
uv venv
uv sync --dev
```

## Required environment variables

Copy `.env.example` to `.env` and adjust as needed.

- `DATABASE_URL`
- `STORAGE_ROOT`
- `ENCRYPTION_KEY`

## Running the app

```bash
uv run fastapi dev app/main.py
```

## Upload example

```bash
curl -X POST http://127.0.0.1:8000/api/intake/documents \
  -F user_id=student-1 \
  -F document_type=offer_letter \
  -F file=@offer-letter.txt
```

## Test commands

```bash
uv run pytest tests/unit -v
uv run pytest tests/integration -v
```
