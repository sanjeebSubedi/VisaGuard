# VisaGuard

VisaGuard is a FastAPI service for the first F-1 compliance slice: document intake and state extraction.

## What this slice does

- accepts user-labeled `i20`, `ead`, and `offer_letter` uploads
- stores original files encrypted on disk
- parses uploads through a real `docling` adapter boundary
- extracts rule-based document facts
- builds a `student_state_snapshot` with eligibility and review metadata

## Supported file kinds

- `i20` -> PDF only
- `offer_letter` -> PDF only
- `ead` -> image only (`png`, `jpg`, `jpeg`, `tiff`, `bmp`, `webp`)

## Privacy boundaries

### Restricted boundary

- encrypted originals

### Downstream-safe boundary

- extracted facts
- review items
- state snapshots
- redacted retained `offer_letter` text only

`i20` and `ead` persist normalized facts only. `offer_letter` persists normalized facts plus full redacted retained text. The API never returns encrypted original locations or retained-text storage paths.

## Local setup

```bash
uv venv
uv sync --dev
```

Docling is installed through `uv sync --dev` from `pyproject.toml`.

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
  -F file=@offer-letter.pdf
```

## Test commands

```bash
uv run pytest tests/unit -v
uv run pytest tests/integration -v
uv run pytest tests/unit -v && uv run pytest tests/integration -v
```
