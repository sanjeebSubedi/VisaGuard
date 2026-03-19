# VisaGuard Design: Document Intake and State Extraction

## Overview

This spec defines the first implementation slice for VisaGuard: intake of student-provided immigration/employment documents and extraction of a downstream-safe student state snapshot.

The slice accepts three user-labeled document types:

- `i20`
- `ead`
- `offer_letter`

The system parses uploaded documents with `docling`, stores original files encrypted, redacts direct identifiers before downstream use, extracts document-specific facts, normalizes them into canonical fields, and assembles a provisional `student_state_snapshot` with confidence markers and review items.

The output of this slice is meant to support later compliance and timeline agents, but this slice does not itself make compliance decisions.

## Goals

- Accept uploads for `i20`, `ead`, and `offer_letter`
- Require the user to identify document type at upload time
- Store original documents encrypted for traceability and re-processing
- Run `docling` on the original document inside a restricted ingestion boundary
- Redact direct identifiers before content leaves the restricted boundary
- Use document-specific extractors for each document type
- Produce canonical structured facts with provenance and confidence
- Build a provisional `student_state_snapshot` for downstream consumers
- Create review items for missing, conflicting, or low-confidence fields
- Prevent unresolved/provisional facts from being used by downstream compliance automation

## Non-Goals

- Compliance reasoning or status determination
- Timeline calculation or deadline alerts
- Partial-scan or severely degraded document handling
- OCR optimization beyond what is needed for normal readable uploads
- Automatic advisor/DSO workflows beyond escalation-ready review items

## Design Principles

- Privacy first: direct identifiers are redacted before downstream use
- Traceability: every canonical field must be traceable to its source document and extraction evidence
- Durable stages: each processing stage persists its artifact so later improvements can re-run from the right boundary
- Explicit uncertainty: low-confidence and conflicting facts are first-class outputs, not hidden failures
- Safe downstream contract: only eligible facts can flow into later compliance logic

## High-Level Architecture

The first slice uses a document-centric workflow with durable artifacts:

1. Encrypted original document stored
2. `docling` parse artifact created inside restricted boundary
3. Redacted downstream-safe derivative created
4. Document-specific extractor emits candidate facts
5. Normalization merges candidates into canonical fields
6. `student_state_snapshot` assembled with review items and eligibility markers

The system boundary is split into two zones:

- Restricted ingestion boundary
  - Encrypted originals
  - Raw `docling` parse output
  - Access-controlled metadata tied to raw artifacts
- Downstream-safe boundary
  - Redacted text/structured derivatives
  - Extracted facts
  - Confidence markers
  - Review items
  - `student_state_snapshot`

Downstream agents may only consume downstream-safe artifacts and only for fields marked eligible for use.

## Core Components

### Upload Service

Responsibilities:

- Accept uploads
- Require explicit document type from the user
- Validate supported types: `i20`, `ead`, `offer_letter`
- Store encrypted original file
- Create the initial document/intake job record
- Compute a stable file fingerprint for deduplication and traceability

### Parsing Stage

Responsibilities:

- Run `docling` on the encrypted original within the restricted boundary
- Persist the parse artifact
- Record parser version and parsing metadata
- Expose parse status for retries and diagnostics

### Redaction Stage

Responsibilities:

- Remove direct identifiers from parsed content before downstream use
- Produce redacted derivative artifacts suitable for extractors and later agents
- Block further downstream processing if redaction fails

Direct identifiers in scope for redaction in this slice:

- Name
- SEVIS ID
- A-number
- Date of birth
- Address
- Phone number
- Email address

Employment identifiers and compensation details remain available in downstream-safe artifacts for extraction and later compliance reasoning.

### Document-Specific Extraction Stage

Responsibilities:

- Route to the extractor matched to the user-selected document type
- Extract candidate facts with provenance and confidence
- Preserve source location references where practical
- Emit document-type-specific outputs

Initial extraction expectations by document type:

- `i20`
  - school/program information
  - program start/end dates
  - CIP/program metadata
  - SEVIS-related academic state fields
  - practical training details present on the form
- `ead`
  - card validity dates
  - category/class information
  - authorization identifiers and status windows
- `offer_letter`
  - employer name
  - role/title
  - employment start date
  - compensation and work arrangement fields if present

### Normalization and Merge Stage

Responsibilities:

- Map extracted candidates into canonical field names/types
- Apply source precedence rules by field category
- Detect missing fields, conflicts, and low-confidence fields
- Determine whether each field is eligible for downstream use
- Assemble the current `student_state_snapshot`

Initial precedence guidance:

- Employment authorization facts: prefer `ead`
- Academic/program/school facts: prefer `i20`
- Employer/job-offer facts: prefer `offer_letter`

Meaningful contradictions still create review items even when a precedence winner exists.

### Review Engine

Responsibilities:

- Create review items for:
  - missing required fields
  - conflicting facts
  - low-confidence facts
- Route straightforward resolution to the student first
- Mark cases suitable for advisor/DSO escalation when ambiguity remains or carries policy significance
- Keep unresolved facts visible to humans but blocked for downstream automation

## Data Flow

### End-to-End Flow

1. User uploads a document and selects its type
2. System stores encrypted original and creates a document record
3. Parsing stage runs `docling`
4. Redaction stage produces downstream-safe derivative
5. Document-specific extractor emits candidate facts
6. Normalization merges facts into canonical fields
7. Review engine creates review items where needed
8. System materializes a provisional `student_state_snapshot`

### Fact Lifecycle

Each extracted candidate fact carries:

- `field_name`
- `value`
- `document_id`
- `document_type`
- `source_location`
- `confidence`
- `status`

Supported fact status values:

- `verified`
- `provisional`
- `missing`
- `conflict`

### Snapshot Eligibility Rules

Each snapshot field has two separate ideas:

- visibility to humans
- eligibility for downstream automated use

Rules:

- Verified, non-conflicted facts may be eligible
- Low-confidence facts remain visible but ineligible
- Missing fields remain ineligible
- Conflicted fields remain ineligible until review resolves them
- Provisional facts may appear in the snapshot but cannot be consumed by downstream compliance agents until resolved/approved

## Initial Data Contract

### `document`

Tracks the uploaded file and stage progress.

Suggested fields:

- `id`
- `user_id`
- `document_type`
- `encrypted_original_uri`
- `file_fingerprint`
- `parse_status`
- `redaction_status`
- `extraction_status`
- `parser_version`
- `extractor_version`
- `created_at`
- `updated_at`

### `document_fact`

Stores extracted candidate facts.

Suggested fields:

- `id`
- `document_id`
- `field_name`
- `value`
- `normalized_value`
- `confidence`
- `status`
- `source_location`
- `created_at`

### `review_item`

Captures resolution work required before safe downstream use.

Suggested fields:

- `id`
- `user_id`
- `snapshot_id`
- `review_type` (`missing_field`, `conflict`, `low_confidence`)
- `field_name`
- `priority`
- `assigned_role` (`student`, `advisor_or_dso`)
- `resolution_status`
- `created_at`

### `student_state_snapshot`

Represents the canonical downstream contract.

Suggested fields:

- `id`
- `user_id`
- `version`
- `snapshot_payload`
- `field_eligibility_map`
- `provenance_map`
- `created_at`

The snapshot should expose winning values plus enough provenance to trace each field back to its source fact.

## Error Handling

### Upload Failures

- If encrypted storage fails, intake fails immediately
- No parsing starts until the original is durably stored

### Parse Failures

- Document transitions to `parse_failed`
- Error is retryable without re-uploading
- Other uploaded documents may continue independently

### Redaction Failures

- Document is blocked from all downstream-safe stages
- Raw artifacts remain restricted
- No extractor or downstream consumer may receive unredacted content

### Extraction Failures

- Preserve prior artifacts
- Mark the document as extraction-failed/retryable
- Do not discard parse or redaction work

### Normalization / Merge Issues

- Still create/update the provisional snapshot when possible
- Emit review items for conflicts, missing fields, or low confidence
- Keep unresolved fields ineligible for downstream compliance use

## User and Reviewer Experience

### Student Responsibilities

- Upload documents
- Specify document type for each upload
- Review straightforward missing/conflicting fields
- Confirm or correct provisional values where appropriate

### Advisor/DSO Escalation

Escalation should be prepared for, but not deeply automated in this slice. The system must support handing off unresolved or policy-significant review items to an advisor/DSO path later.

## Testing Strategy

### Unit Tests

- Document-type routing
- Redaction of direct identifiers
- Canonical field mapping
- Source precedence rules
- Confidence threshold behavior
- Eligibility blocking rules

### Fixture / Golden Tests

Use realistic, readable fixture sets for:

- `i20`
- `ead`
- `offer_letter`

Include cases for:

- conflicting dates across documents
- missing fields
- low-confidence extraction outputs
- clean successful extraction paths

The MVP assumes no partial scans.

### Integration Tests

Verify the artifact chain:

- encrypted original stored
- `docling` parse saved
- redacted derivative produced
- candidate facts extracted
- snapshot assembled
- review items created when needed

### Privacy / Security Tests

Verify direct identifiers do not appear in downstream-safe artifacts after redaction.

### Regression Tests

Pin behavior for:

- precedence resolution
- conflict handling
- provisional fact blocking
- snapshot eligibility decisions

## Out of Scope for This Spec

The following belong to later slices:

- Compliance decision agents
- OPT/CPT timeline engine
- Deadline monitoring and notifications
- Policy retrieval/reasoning over USCIS guidance
- Full institutional review workflow tooling

## Planning Readiness

This spec is ready to be turned into an implementation plan for a single focused slice:

- one ingestion pipeline
- three supported document types
- one canonical downstream contract
- one review/eligibility boundary for later compliance agents

No implementation work should start until planning breaks this into concrete milestones, schemas, and tests.
