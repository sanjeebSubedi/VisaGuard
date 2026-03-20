# VisaGuard Design: Ollama-Based LLM Extraction Upgrade

## Overview

This spec replaces the current regex-based document extraction layer with a local Ollama-based LLM extraction flow while keeping deterministic validation and downstream compliance state assembly in place.

The current system already:

- accepts `i20`, `ead`, and `offer_letter` uploads
- stores encrypted originals
- parses documents with Docling
- persists normalized facts and snapshots

The weakness is extraction quality. Real Docling output from PDFs and OCR text from images does not reliably preserve simple `key: value` adjacency, so the current regex extractors underperform on real-world documents. This upgrade moves semantic extraction to a local LLM hosted with Ollama and keeps deterministic validation after extraction.

## Goals

- Replace regex-first extraction with Ollama-based extraction for all supported document types
- Use one configured local model: `qwen3:4b-instruct`
- Keep Docling as the parsing layer
- Use separate extraction prompts for `i20`, `ead`, and `offer_letter`
- Require strict JSON output from the LLM
- Return normalized values only from the LLM
- Retry once for malformed JSON
- Retry once for missing required fields
- Persist `null` for fields still missing after the second pass
- Keep deterministic validators for date formats, required fields, conflicts, and eligibility rules
- Persist raw LLM JSON plus model and prompt version metadata for debugging
- Keep upload processing synchronous
- Keep the existing upload, snapshot, and review-item API shape stable

## Non-Goals

- Running extraction asynchronously in the background
- Adding fallback rule-based extraction when Ollama is unavailable
- Using multiple Ollama models per document type in this slice
- Asking the LLM to perform downstream compliance reasoning
- Returning evidence snippets or confidence from the LLM in this first version
- Reworking the snapshot contract consumed by downstream logic

## Design Principles

- LLM-first for semantic extraction
- Deterministic validation after extraction
- Separate prompts per document type
- Strict JSON only
- Bounded retry behavior
- Strong local debugging surface
- Stable downstream state contract

## High-Level Architecture

The intake pipeline remains:

1. upload accepted
2. encrypted original stored
3. Docling parses document
4. extraction runs
5. normalized facts persist
6. deterministic validators and snapshot assembly run

The key change is step 4.

Instead of routing parsed text to regex extractors, the system routes parsed text to an Ollama-backed LLM extractor using `qwen3:4b-instruct`. Each document type gets its own prompt file and response model. The LLM returns strict JSON containing only normalized field values for that document type.

After extraction, deterministic logic still owns:

- required-field checks
- date and format validation
- cross-document conflicts
- eligibility gating
- review-item generation

This keeps extraction flexible and semantic without letting compliance-critical decisions depend entirely on the model.

## Core Components

### Ollama Client Adapter

Responsibilities:

- wrap the Ollama Python library
- call the local Ollama runtime
- send model name, prompt, and inference settings
- enforce request timeout behavior
- return raw text responses to the extractor service
- surface clear errors when Ollama is unavailable

This adapter should be the only place in the app that knows Ollama client details.

### Prompt Registry

Responsibilities:

- store prompt files for `i20`, `ead`, and `offer_letter`
- define exactly which fields to extract for each document type
- require strict JSON output only
- instruct the model to return `null` for unknowns

Prompt style should be compact because the chosen local model has only 4B parameters and should not be overwhelmed with unnecessary instruction overhead.

### Response Models

Responsibilities:

- define the expected JSON shape for each document type
- parse strict JSON from the model
- represent optional fields as `null`/`None`
- create a stable mapping from LLM output into normalized facts

Prompt text lives in files; response validation lives in Python.

### LLM Extractor Service

Responsibilities:

- choose the document-type prompt
- perform first-pass extraction
- attempt one malformed-JSON repair if needed
- detect missing required fields
- perform one second-pass retry for missing fields using the full parsed text again
- merge retry results into the first-pass result
- return normalized field values plus raw JSON/debug metadata

This service owns extraction orchestration, not downstream compliance validation.

### Deterministic Validation Layer

Responsibilities:

- validate dates and structured formats
- identify missing required fields
- detect cross-document conflicts
- preserve downstream eligibility and review-item behavior

The validators operate after the LLM has extracted candidate normalized values.

### Persistence Extensions

Responsibilities:

- keep persisting normalized facts
- persist raw LLM JSON for debugging
- persist extractor metadata including:
  - model name
  - prompt version
  - extractor version

This allows prompt iteration and debugging without exposing these internals in downstream-safe API responses.

## Prompt and Schema Strategy

### Document-Type-Specific Prompts

The system uses separate prompts for:

- `i20`
- `ead`
- `offer_letter`

Each prompt should:

- state the document type specialist role
- list exactly which fields to extract
- require strict JSON only
- instruct `null` for unknown values
- forbid explanatory prose

### Strict JSON Contract

The LLM returns only normalized values, not confidence or evidence.

Example shape:

```json
{
  "program_start_date": "2026-08-20",
  "cip_code": "11.0701",
  "school_name": "Example University"
}
```

Unknown fields should be:

```json
{
  "program_start_date": null
}
```

### Required vs Optional Fields

Python response models should distinguish:

- fields required for the schema shape
- fields required for downstream workflow

The model can return `null`; deterministic validators decide whether that creates a review item or blocks downstream use.

## Data Flow

1. upload passes document-type validation
2. encrypted original is stored
3. Docling parses the document into text
4. LLM extractor service selects prompt + response model by document type
5. Ollama adapter sends full parsed text to `qwen3:4b-instruct`
6. response is parsed as strict JSON
7. if JSON is malformed, one repair attempt runs
8. if required fields are missing, one retry runs for only the missing fields using the full parsed text again
9. any still-missing fields become `null`
10. normalized facts persist
11. raw LLM JSON and extractor metadata persist for debugging
12. deterministic validation and snapshot assembly run

## Retry and Failure Behavior

### Ollama Unavailable

- fail the upload request immediately
- return a clear extraction error
- do not fall back to regex extraction
- do not silently mark extraction pending

### Malformed JSON

- first response must parse as strict JSON
- if it does not, perform one repair attempt asking for valid JSON only
- if repair still fails, fail extraction and return an error

### Missing Required Fields

- after valid JSON is parsed, inspect required fields
- if required fields are missing, run one second-pass extraction for only those fields
- use the full parsed text again rather than heuristically narrowed excerpts
- merge second-pass results into the first-pass result
- if fields are still missing, persist `null`

### Post-Extraction Validation Failure

- keep raw LLM JSON and metadata for debugging
- mark facts or fields according to deterministic validation outcomes
- allow downstream review-item logic to surface the issue

## Persistence Model

The system continues to persist normalized facts per document, and additionally persists extraction debug artifacts.

Recommended stored extraction metadata:

- `model_name`: `qwen3:4b-instruct`
- `prompt_version`
- `extractor_version`
- `raw_llm_json`

This data is internal only and should not be exposed in the current outward API responses.

## Manual Testing and Developer Experience

The upload API remains the manual testing surface.

Developers should be able to:

- start Ollama locally
- pull `qwen3:4b-instruct`
- start the API locally
- upload `i20`, `ead`, and `offer_letter` documents manually
- inspect:
  - upload response
  - latest snapshot
  - review items
  - persisted normalized facts
  - raw LLM JSON
  - retained redacted `offer_letter` text

The local setup docs should include example commands for these flows.

## Error Handling

### Parse Failure

Docling failures continue to behave as they do now:

- document becomes `parse_failed`
- extraction does not run

### Extraction Failure

If the LLM extraction path fails hard:

- request fails immediately
- no silent fallback extraction runs

### Partial Extraction

If extraction succeeds structurally but some fields remain missing:

- those fields become `null`
- deterministic validators generate missing-field outcomes

## Testing Strategy

### Unit Tests

- Ollama adapter request/response handling
- malformed JSON repair behavior
- missing-fields retry behavior
- response model parsing
- prompt-version/model metadata capture

### Integration Tests

- successful upload for `i20`, `ead`, and `offer_letter` using mocked Ollama responses
- Ollama unavailable -> request failure
- malformed JSON after repair failure -> request failure
- missing fields after second pass -> `null` persisted and review items generated
- snapshot contract remains stable after the extraction upgrade

### Live Regression Tests

- use real sample documents to measure whether prompt changes improve extraction
- use these fixtures as a regression harness for ongoing prompt tuning

## Open Implementation Notes

- keep prompts short and explicit for `qwen3:4b-instruct`
- centralize model name in configuration
- keep Ollama-specific logic behind a thin adapter
- prefer versioned prompt files so prompt changes can be audited
- retain deterministic validators as the safety boundary around LLM extraction

## Summary

This upgrade changes VisaGuard from brittle regex extraction to local LLM-based semantic extraction while preserving deterministic compliance-oriented validation after extraction.

The result is:

- better extraction from real Docling output
- a local-only inference path using Ollama
- bounded retries and explicit failure modes
- stable downstream snapshot behavior
- improved debugging through persisted raw LLM output and prompt/model version metadata
