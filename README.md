# VisaGuard

VisaGuard is a FastAPI service for the first F-1 compliance slice: document intake and state extraction.

## What this slice does

- accepts user-labeled `i20`, `ead`, and `offer_letter` uploads
- stores original files encrypted on disk
- parses uploads through a real `docling` adapter boundary
- extracts normalized facts through a local Ollama-backed LLM layer
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

Docling and the Ollama Python client are installed through `uv sync --dev` from `pyproject.toml`.

## Required environment variables

Copy `.env.example` to `.env` and adjust as needed.

- `DATABASE_URL`
- `STORAGE_ROOT`
- `ENCRYPTION_KEY`
- `OLLAMA_HOST`
- `OLLAMA_MODEL`
- `OLLAMA_TIMEOUT_SECONDS`

Default extraction model: `qwen3:4b-instruct`
Default Ollama timeout: `180` seconds

## Start Ollama

Install and start Ollama locally, then pull the configured model:

```bash
ollama serve
ollama pull qwen3:4b-instruct
```

## Running the app

```bash
uv run --with uvicorn uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The app now initializes database tables on startup, so a clean local run does not need a separate bootstrap command.

## Timeline manager

The repo now includes a deterministic timeline manager under `app/services/timeline/`.

- it reads extracted facts only in v1
- it accepts an explicit `evaluation_date` for deterministic replay/testing
- it computes structured `timeline_inputs` and `timeline_status`
- it covers OPT/STEM unemployment, reporting windows, grace periods, and Cap-Gap when enough facts are present

## Upload examples

```bash
curl -X POST http://127.0.0.1:8000/api/intake/documents \
  -F user_id=student-1 \
  -F document_type=offer_letter \
  -F file=@offer-letter.pdf
```

```bash
curl -X POST http://127.0.0.1:8000/api/intake/documents \
  -F user_id=student-1 \
  -F document_type=i20 \
  -F file=@documents/i20.pdf
```

```bash
curl -X POST http://127.0.0.1:8000/api/intake/documents \
  -F user_id=student-1 \
  -F document_type=ead \
  -F file=@documents/ead.png
```

## Inspect results

```bash
curl http://127.0.0.1:8000/api/intake/users/student-1/snapshot
curl http://127.0.0.1:8000/api/intake/users/student-1/review-items
```

## Test commands

```bash
uv run pytest tests/unit -v
uv run pytest tests/integration -v
uv run pytest tests/unit -v && uv run pytest tests/integration -v
uv run pytest tests/unit/test_timeline_*.py tests/integration/test_timeline_manager.py -v
```
