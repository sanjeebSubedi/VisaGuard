# VisaGuard Design: I-20 Few-Shot Prompt and Schema Upgrade

## Overview

This spec narrows the next extraction improvement to the `i20` document type only.

The current Ollama-based extraction system works end-to-end, but the I-20 extraction contract is too small and the I-20 prompt is too generic for a 4B local model. Right now, the system only asks for:

- `program_start_date`
- `cip_code`
- `school_name`

This upgrade expands the I-20 extraction contract to include the full field set needed for downstream compliance state and rewrites the I-20 prompt into a specialized few-shot prompt tailored for `qwen3:4b-instruct`.

`ead` and `offer_letter` remain unchanged in this slice so we can isolate whether prompt specialization improves real extraction quality.

## Goals

- Expand the I-20 extraction contract to include the full agreed field set
- Treat only a subset of those fields as required for validation/retry behavior
- Rewrite the I-20 prompt into a specialized few-shot prompt
- Keep the current Ollama + Docling + validation pipeline unchanged
- Preserve current `ead` and `offer_letter` behavior
- Keep outward upload, snapshot, and review-item APIs unchanged

## Non-Goals

- Changing `ead` prompting in this slice
- Changing `offer_letter` prompting in this slice
- Changing the overall extraction orchestration flow
- Adding new retries beyond the existing malformed-JSON repair and missing-fields retry
- Adding confidence or evidence output from the LLM
- Changing downstream compliance reasoning

## I-20 Field Contract

### Required fields

- `sevis_id`
- `surname`
- `given_name`
- `cip_code`
- `major`
- `education_level`
- `school_name`

### Optional fields

- `school_code`
- `program_start_date`
- `program_end_date`

The required/optional split affects only validation and missing-field review behavior. All fields remain part of the schema and may be returned when present.

## Design Principles

- Keep the change isolated to `i20`
- Improve prompt quality before adding more architecture
- Optimize for a small local model
- Keep the extraction pipeline behavior stable
- Use few-shot examples to improve field mapping and normalization

## High-Level Architecture

The pipeline remains:

1. upload accepted
2. Docling parses text
3. I-20 prompt selected
4. Ollama returns strict JSON
5. schema parses output
6. retry logic runs if needed
7. validators run
8. facts and snapshot persist

Only the I-20 prompt, I-20 schema, and I-20 required-field configuration change.

This means:

- no API contract changes
- no lifecycle/state machine changes
- no new background jobs
- no changes to `ead` or `offer_letter`

## Core Components

### I-20 Prompt File

Responsibilities:

- define the full I-20 field list
- clearly separate required and optional fields
- provide document-specific extraction guidance
- include normalization instructions
- include one or two compact few-shot examples
- require strict JSON only with `null` for unknowns

Because the active model is small, the prompt should be highly specific and avoid unnecessary wording.

### I-20 Response Schema

Responsibilities:

- represent the full 10-field I-20 extraction contract
- parse strict JSON output from the model
- allow `null` for optional or missing values

The schema should remain the source of truth for what an I-20 extraction result can contain.

### Prompt Registry

Responsibilities:

- expose the updated I-20 prompt version
- expose the updated I-20 required-field set
- keep `ead` and `offer_letter` definitions unchanged

### Validation Layer

Responsibilities:

- continue treating required I-20 fields as missing-field triggers
- ignore missing optional I-20 fields for missing-field review generation
- keep the current retry/validation behavior otherwise unchanged

## Prompt Strategy

The new I-20 prompt should not be just a field list. It should be a specialized extractor prompt for SEVIS Form I-20 documents.

Recommended prompt structure:

1. role definition:
   - expert extractor for SEVIS Form I-20
2. extraction target:
   - exact field names to return
3. required/optional guidance:
   - required fields must be extracted when possible
   - optional fields may be `null`
4. normalization rules:
   - preserve field names exactly
   - return dates in normalized string form when clearly present
   - return `null` instead of guessing
5. few-shot examples:
   - one or two compact examples showing realistic I-20 text fragments and exact JSON output
6. final output rule:
   - strict JSON only, no prose

## Data Flow

1. user uploads `i20`
2. Docling parses the PDF
3. prompt registry selects the upgraded few-shot I-20 prompt
4. `qwen3:4b-instruct` receives the parsed text and specialized prompt
5. model returns strict JSON for the expanded I-20 schema
6. JSON is parsed into the updated I-20 response model
7. if required fields are missing, the existing retry logic runs
8. optional fields may remain `null`
9. normalized facts continue through validation and snapshot assembly

## Error Handling

### Malformed JSON

No change:

- one repair attempt only

### Missing required I-20 fields

No change to the orchestration:

- missing required I-20 fields trigger the existing second-pass retry
- if still missing, they remain `null` and generate review items

### Missing optional I-20 fields

- `school_code`
- `program_start_date`
- `program_end_date`

These may remain `null` without being treated as missing required data.

### Other document types

No change:

- `ead` remains as-is
- `offer_letter` remains as-is

## Testing Strategy

### Unit tests

- update I-20 schema tests to cover all 10 fields
- verify required and optional I-20 fields are configured correctly in the prompt registry
- verify the updated I-20 prompt is loaded and versioned correctly

### Extraction tests

- verify the LLM extraction service can parse an expanded I-20 JSON payload
- verify missing optional fields can remain `null`
- verify missing required fields still participate in retry/validation behavior

### Integration tests

- update mocked I-20 extraction results to include the expanded field set
- verify the new I-20 fields can flow into persisted facts and snapshot/review processing
- keep `ead` and `offer_letter` tests stable to ensure this slice is isolated

### Manual validation

Use a real I-20 sample to compare:

- extraction quality before prompt change
- extraction quality after prompt change

This slice is specifically about testing whether a specialized few-shot prompt improves I-20 extraction quality on a small local model.

## Summary

This upgrade is a focused experiment with high practical value:

- expand the I-20 extraction schema to the full desired field set
- treat only the right subset as required
- replace the generic I-20 prompt with a specialized few-shot prompt
- keep the rest of the Ollama extraction architecture unchanged

If this improves real I-20 extraction quality, the same few-shot strategy can then be applied to `ead` and `offer_letter` in later slices.
