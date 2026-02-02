# VisaGuard

A tool to help F-1 students stay compliant with OPT regulations.

## What it does

VisaGuard extracts key information from immigration documents (I-20, EAD cards, offer letters) and tracks compliance deadlines. It runs entirely locally using Ollama, so your documents never leave your machine.

**Current features:**
- Extract fields from I-20s, EAD cards, and offer letters
- Duplicate detection (won't reprocess the same file)
- SQLite storage for extracted data
- Date normalization and validation

## Quick start

```bash
# Install dependencies
uv sync

# Make sure Ollama is running with the model
ollama pull qwen3:4b-instruct

# Process a document
uv run python -m app.services.document_processor offer
```

## Demo

The `poc` branch has a working Streamlit demo you can run:

```bash
git checkout poc
uv run streamlit run app.py
```

## Project structure

```
app/
├── db/          # SQLite models and database logic
└── services/    # Document processing, prompts, schemas
data/
├── templates/   # Sample documents for testing
tests/
└── unit/        # pytest tests
```

## Tech stack

Python, Ollama (Qwen3-4B), LangChain, Docling, SQLModel, Pydantic

## Status

Work in progress. Core extraction pipeline is functional. Timeline tracking and policy agent are next.
