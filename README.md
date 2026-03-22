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
- `LANGGRAPH_CHECKPOINTER_PATH`

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


## Policy agent

The repo now includes a grounded policy agent under `app/services/policy_agent/`.

- it reads structured academic and job facts only in v1
- it uses a local `cip_code` JSON dataset plus local policy source files
- it uses a prebuilt local hybrid retrieval index
- it writes structured `policy_analysis` and `policy_verdict` outputs

### Policy data and index

- CIP dataset: `data/policy/cip_codes.json`
- policy sources: `data/policy/sources/`
- default index path: `data/policy/index/policy_index.json`

Build or refresh the local policy index with:

```bash
uv run python - <<'PYCMD'
from pathlib import Path

from app.core.config import Settings
from app.services.policy_agent.indexer import build_policy_index

settings = Settings()
policy_root = Path(settings.policy_data_root)

build_policy_index(
    cip_dataset_path=policy_root / "cip_codes.json",
    policy_sources_dir=policy_root / "sources",
    output_path=Path(settings.policy_index_path),
)
PYCMD
```

## Compliance agent

The repo now includes a deterministic compliance agent under `app/services/compliance/`.

- it reads only `timeline_status` and `policy_verdict`
- it normalizes those upstream outputs into internal pass/fail/unknown flags
- it applies a pessimistic decision matrix where the worst legally relevant condition wins
- it writes a strict `final_compliance_record` with `overall_state`, `severity`, `action_plan`, and `audit_summary`

## LangGraph workflow

The repo now includes a callable LangGraph workflow that orchestrates the three evaluators.

- it loads the latest stored snapshot by `user_id`
- it runs `timeline` and `policy` in parallel
- it fans in to `compliance`
- it stores only the latest workflow result in the app DB
- it uses a LangGraph checkpointer for execution history keyed by `thread_id = user_id`

Run the full workflow with:

```bash
curl -X POST http://127.0.0.1:8000/api/workflows/compliance/run \
  -H 'Content-Type: application/json' \
  -d '{"user_id": "student-1", "evaluation_date": "2026-03-22"}'
```

Before using the workflow endpoint, make sure the policy index exists at `data/policy/index/policy_index.json` or your configured `POLICY_INDEX_PATH`.

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

## Manual EAD entry

If you do not have an EAD image handy, you can create a manual EAD entry that feeds the same snapshot, timeline, and policy flows.

```bash
curl -X POST http://127.0.0.1:8000/api/intake/ead/manual \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "student-1",
    "alien_registration_number": "A123456789",
    "category": "C03B",
    "card_start_date": "2026-08-20",
    "card_end_date": "2027-08-19",
    "card_number": "EAD1234567"
  }'
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
uv run pytest tests/unit/test_policy_*.py tests/integration/test_policy_agent_integration.py -v
uv run pytest tests/unit/test_compliance_*.py tests/integration/test_compliance_agent.py -v
uv run pytest tests/unit/test_graph_*.py tests/unit/test_workflow_results.py tests/integration/test_workflow_api.py -v
```
