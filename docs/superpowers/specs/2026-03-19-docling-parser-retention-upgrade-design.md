# VisaGuard Design: Real Docling Parsing and Document Retention Policy Upgrade

## Overview

This spec upgrades the current document intake slice from a parser stub to a production-oriented parsing and retention design.

The current system accepts uploads for:

- `i20`
- `ead`
- `offer_letter`

but it does not yet use real Docling parsing. This upgrade replaces the stub parser with a real Docling adapter, adds strict document-type-specific file validation, and introduces explicit retention policy rules per document type while keeping the outward `student_state_snapshot` and review-item APIs unchanged.

## Goals

- Replace the current parser stub with real Docling integration
- Support real PDF parsing for `i20` and `offer_letter`
- Support real image parsing for `ead`
- Enforce document-type-specific file validation at upload time
- Preserve encrypted originals for all document types
- Persist normalized facts for all document types
- Persist full redacted retained text only for `offer_letter`
- Keep the existing snapshot and review-item API contract stable
- Surface parser failures as explicit `parse_failed` states

## Non-Goals

- Changing the outward shape of `student_state_snapshot`
- Introducing a second fallback OCR/parser stack in this slice
- Supporting scanned-image PDFs for `i20` or `offer_letter`
- Persisting full Docling raw parse artifacts long-term
- Adding a frontend upload flow in this slice

## Design Principles

- Production parser, not parser stub
- Explicit policy per document type
- Encrypted originals retained for reprocessing
- Minimal persistence: facts for all documents, retained text only where needed
- Stable downstream API contract
- Visible failure states for validation, parsing, extraction, and retention

## High-Level Architecture

The upgraded system keeps one shared intake pipeline, but introduces a document policy layer that controls parsing and retention behavior by document type.

Policy rules:

- `i20`
  - allowed input: PDF
  - parser: Docling
  - persistence: normalized facts only
- `ead`
  - allowed input: image
  - parser: Docling
  - persistence: normalized facts only
- `offer_letter`
  - allowed input: PDF
  - parser: Docling
  - persistence: normalized facts plus full redacted retained text

The current `student_state_snapshot` flow remains unchanged:

1. upload accepted
2. encrypted original stored
3. parse executed
4. document-specific extraction performed
5. review/normalization pipeline runs
6. canonical snapshot updated

The main architectural change is that redaction is no longer a universal pre-extraction step. Redaction becomes a document-type-specific retention step used only for the stored `offer_letter` text artifact.

## Core Components

### Upload Validator

Responsibilities:

- require declared `document_type`
- validate file type before storage/parsing
- reject mismatched uploads immediately

Validation rules:

- `i20` -> PDF only
- `offer_letter` -> PDF only
- `ead` -> image only

This validator should use both MIME type and filename extension where practical, with a bias toward rejecting obviously mismatched inputs early.

### Docling Parser Adapter

Responsibilities:

- replace the current text-decoding stub
- accept both PDF and image inputs
- invoke Docling in a single controlled adapter layer
- return normalized parser output for extractors
- surface parser failures as structured internal errors/status updates

This adapter is the only place in the application that should know Docling invocation details.

### Document Policy Layer

Responsibilities:

- define allowed file types per document type
- declare whether retained text is persisted
- declare whether redaction is required
- define parser mode expectations by document type

This policy layer makes behavior differences explicit instead of burying them in conditionals throughout the pipeline.

### Extraction Stage

Responsibilities:

- consume normalized Docling output
- route to existing document-type-specific extractors
- emit normalized facts for:
  - `i20`
  - `ead`
  - `offer_letter`

Extractor responsibilities do not fundamentally change in this slice, but their input source changes from stub text decoding to real Docling parse results.

### Retention Handler

Responsibilities:

- persist normalized facts for all document types
- persist full redacted retained text only for `offer_letter`
- avoid persisting parser text for `i20` or `ead`

Retention policy:

- `i20` -> no retained parser text
- `ead` -> no retained parser text
- `offer_letter` -> persist full redacted text artifact

### Snapshot / Review Updater

Responsibilities:

- reuse the current normalization, precedence, review-item, and eligibility logic
- keep outward snapshot behavior stable
- consume the same normalized facts contract as before

No downstream consumer should need to change because of this parser upgrade.

## Data Flow

### Shared Flow

1. user uploads file with declared `document_type`
2. upload validator checks file type against policy
3. encrypted original is stored
4. Docling parses the original within the restricted boundary
5. extractor emits normalized facts
6. retention policy runs
7. snapshot/review logic updates canonical state

### Per-Document Persistence

#### `i20`

- store encrypted original
- parse with Docling
- extract normalized facts
- persist facts only
- discard transient parser text after extraction

#### `ead`

- store encrypted original
- parse image with Docling
- extract normalized facts
- persist facts only
- discard transient parser text after extraction

#### `offer_letter`

- store encrypted original
- parse with Docling
- extract normalized facts
- redact full parsed text
- persist facts plus full redacted retained text

## Privacy and Retention Model

### Encrypted Originals

All uploaded originals remain stored encrypted:

- `i20`
- `ead`
- `offer_letter`

Reason:

- enables later reprocessing if parsing/extraction improves
- preserves traceability without expanding downstream data exposure

### Persisted Downstream Data

- `i20` -> normalized facts only
- `ead` -> normalized facts only
- `offer_letter` -> normalized facts plus full redacted retained text

### Redaction Scope

Redaction is only required for persisted retained `offer_letter` text.

Direct identifiers remain the agreed set:

- name
- SEVIS ID
- A-number
- date of birth
- address
- phone number
- email address

The goal is no longer “redact everything before extraction.” The goal is “do not persist unredacted offer-letter narrative text.”

## Error Handling

### Validation Failure

- reject request before storage/parsing
- return a clear file-type mismatch error

Examples:

- `ead` uploaded as PDF -> reject
- `i20` uploaded as JPEG -> reject

### Parse Failure

- store encrypted original
- mark document `parse_failed`
- do not continue to extraction
- surface retry/re-upload path

No secondary parser fallback is introduced in this slice.

### Extraction Failure

- preserve encrypted original
- preserve parse success status
- mark extraction failure separately
- allow later investigation of extractor quality without conflating it with parser failure

### Retention Failure

Applies only to retained `offer_letter` text:

- if redaction fails, do not persist retained text
- fail the document visibly rather than storing unredacted text
- keep encrypted original for later retry/debugging

## API Contract

The outward API contract remains stable:

- upload endpoint still accepts `document_type`
- snapshot endpoint still returns canonical state
- review-items endpoint still returns review items

This slice changes internal parsing and retention behavior, not the consumer-facing state model.

## Testing Strategy

### Unit Tests

- document policy rules by type
- file-type validation rules
- Docling adapter success/failure behavior
- retention behavior per document type
- `offer_letter` redaction for retained text

### Parser Tests

Verify Docling adapter behavior for:

- PDF inputs
- image inputs
- parser failure propagation

### Integration Tests

Required scenarios:

- `i20` PDF upload -> facts persisted, no retained text
- `ead` image upload -> facts persisted, no retained text
- `offer_letter` PDF upload -> facts persisted, full redacted retained text persisted
- invalid upload type/file combinations rejected
- Docling parse failure becomes `parse_failed`

### Privacy Tests

Verify:

- no retained unredacted `offer_letter` text is persisted
- `i20` and `ead` do not persist retained parser text
- encrypted-original storage paths are not exposed in downstream-safe API responses

## Implementation Impact

Expected internal changes:

- replace parser stub in the Docling adapter
- add document policy layer
- update upload validation
- modify pipeline retention behavior
- add storage support for retained redacted `offer_letter` text
- keep snapshot/review APIs compatible

Expected non-changes:

- no new external snapshot contract
- no new OCR fallback system
- no new frontend work

## Planning Readiness

This spec is focused enough for a single implementation plan:

- real Docling integration
- explicit file validation
- policy-driven document retention
- no downstream API breakage

It should be implemented before starting the next product slice so the intake system is a real working parser rather than a stub.
