# VisaGuard Design: Timeline Manager

## Overview

This spec defines the first deterministic compliance timeline slice for VisaGuard.

The current system already:

- accepts `i20`, `ead`, and `offer_letter` uploads
- stores encrypted originals
- parses documents with Docling
- extracts normalized facts with local Ollama-based prompts
- assembles a `student_state_snapshot`

The next missing layer is a deterministic timeline manager that turns extracted facts into compliance clocks, deadlines, risk flags, and action items. This layer is the compliance backbone that later agents, including the policy agent, will consume through LangGraph state.

## Goals

- Build a deterministic timeline manager, not an LLM-based evaluator
- Read document-derived facts only in this first version
- Accept an optional `evaluation_date` and default to the current date when one is not provided
- Compute the first supported compliance timelines:
  - OPT unemployment clock
  - STEM OPT unemployment clock
  - 10-day reporting windows when derivable from document facts
  - grace period windows
  - Cap-Gap window when supported by available facts
- Produce a structured `timeline_status` object
- Produce a compact `timeline_inputs` summary for traceability
- Emit deterministic risk flags and action items
- Mark unsupported or under-specified clocks as `insufficient_data` with missing prerequisites
- Store the resulting timeline outputs in LangGraph state

## Non-Goals

- Using user-entered event updates in this slice
- Generating final compliance verdicts in the timeline manager
- Using an LLM to compute dates or deadlines
- Replacing the extracted student state as source data
- Building the RAG-based policy agent in this spec
- Covering every possible F-1 edge case in the first iteration

## Design Principles

- Deterministic before interpretive
- No guessed dates or silent inference
- Explicit prerequisite tracking
- Small clock calculators with isolated responsibilities
- Replayable timeline evaluation via explicit `evaluation_date`
- LangGraph-friendly structured outputs

## High-Level Architecture

The timeline manager sits after document extraction and snapshot assembly.

The flow is:

1. intake/extraction produces structured student facts
2. those facts are loaded into LangGraph state
3. the timeline manager reads the relevant facts plus an optional `evaluation_date`
4. independent clock calculators evaluate supported compliance windows
5. a deterministic risk/action layer converts clock states into risk flags and action items
6. the manager writes `timeline_inputs` and `timeline_status` back into LangGraph state

This keeps the timeline layer fully deterministic and makes it a safe input to the later policy agent.

## LangGraph State Contract

### Existing/Source Inputs

The graph state is expected to already contain or make available:

- paths to original documents
- extracted document facts
- `cip_code`
- any currently available employment and authorization dates derived from documents

### New Timeline Outputs

The timeline manager writes:

- `timeline_inputs`
- `timeline_status`

### `timeline_inputs`

`timeline_inputs` is a compact summary of the facts used for computation, not a full duplicate of raw document payloads.

Expected contents:

- `evaluation_date`
- fact names used by each clock
- winning source/provenance summary where useful
- missing prerequisites by clock when applicable

### `timeline_status`

`timeline_status` is the canonical deterministic output for downstream workflow use.

Expected top-level shape:

- `current_phase`
- `clocks`
- `deadlines`
- `risk_flags`
- `action_items`

Each clock entry should contain:

- `status`
- `relevant_dates`
- `days_remaining` or equivalent count when meaningful
- `missing_prerequisites` when `status=insufficient_data`

Supported statuses:

- `active`
- `completed`
- `not_applicable`
- `insufficient_data`

## Core Components

### Timeline Evaluator

Responsibilities:

- accept document-derived facts and optional `evaluation_date`
- route inputs to the correct clock calculators
- collect clock outputs into one deterministic result
- coordinate risk-flag and action-item generation

This is the orchestration layer for the timeline manager.

### Clock Calculators

Each clock calculator should be a focused deterministic module.

Initial calculators:

- OPT unemployment
- STEM OPT unemployment
- reporting windows
- grace periods
- Cap-Gap

Each calculator should:

- declare required input facts
- compute only its own rule family
- return a structured result
- return `insufficient_data` when inputs are missing

### Eligibility / Prerequisite Checker

Responsibilities:

- identify whether each clock has enough facts to run
- list missing prerequisites explicitly
- prevent silent inference when inputs are incomplete or contradictory

This logic can be implemented inside each calculator or through a shared helper, but the output behavior must remain consistent.

### Risk / Action Layer

Responsibilities:

- convert computed timelines into deterministic risk flags
- generate deterministic action items

Examples:

- approaching OPT unemployment limit
- STEM OPT unemployment limit reached or approaching
- reporting window due soon
- grace period ending soon
- Cap-Gap window active or ending soon

Action items should be short, specific, and date-linked where possible.

### Timeline State Assembler

Responsibilities:

- build the final `timeline_inputs`
- build the final `timeline_status`
- normalize outputs into LangGraph-friendly structures

## Supported Timeline Calculations

### OPT Unemployment Clock

Purpose:

- calculate remaining time against the 90-day unemployment limit for OPT when enough facts exist

Outputs:

- current count or derived remaining allowance
- relevant anchor dates
- status
- risk flags/action items if near threshold

### STEM OPT Unemployment Clock

Purpose:

- calculate remaining time against the 150-day cumulative unemployment limit when enough facts exist

Outputs mirror the OPT clock structure.

### 10-Day Reporting Windows

Purpose:

- identify reporting windows that can be derived from document-based facts in this first version

Because this slice uses only document-derived inputs, the system should only evaluate windows when a triggering date can be grounded in extracted state. Otherwise it should return `insufficient_data`.

### Grace Period Windows

Purpose:

- calculate applicable post-completion grace periods when authorization/program end anchors are available

### Cap-Gap Window

Purpose:

- represent Cap-Gap coverage or related status only when supported by extracted facts

If the required facts are not present, this clock should surface `insufficient_data` rather than assume the benefit applies.

## Risk Flags

Risk flags are deterministic, structured, and machine-readable.

Each risk flag should include:

- `type`
- `severity`
- `message`
- related clock or field where applicable

Example categories:

- `deadline_approaching`
- `deadline_passed`
- `limit_approaching`
- `limit_reached`
- `invalid_input`
- `insufficient_data`

## Action Items

Action items are deterministic and derived from calculated clock states.

Each action item should include:

- `type`
- `priority`
- `message`
- due date if available
- related clock

Examples:

- report by a specific date
- review unemployment limit urgently
- confirm missing facts needed for grace period calculation

The action layer should not produce open-ended narrative advice in this slice.

## Evaluation Date Behavior

The timeline manager accepts:

- an explicit `evaluation_date`
- otherwise defaults to the current date

This is important for:

- deterministic testing
- replay/debugging
- historical scenario checks

All automated tests should prefer explicit dates.

## Error Handling

- If some facts are missing, affected clocks return `insufficient_data` instead of failing the whole manager
- If a date is present but malformed, the manager should emit `invalid_input`-style risk flags and avoid misleading deadline output
- If one calculator cannot compute due to bad inputs, other calculators should still run
- If no clocks can be evaluated, the manager should still return a valid `timeline_status` explaining that required inputs are missing

The timeline manager should be resilient and explicit, not brittle.

## Testing Strategy

### Unit Tests

Add focused unit tests for:

- OPT unemployment calculator
- STEM OPT unemployment calculator
- reporting window calculator
- grace period calculator
- Cap-Gap calculator
- invalid input handling
- insufficient data handling
- risk-flag generation
- deterministic action-item generation

### State Assembly Tests

Verify:

- `timeline_inputs` shape
- `timeline_status` shape
- stable handling of `evaluation_date`
- predictable missing-prerequisite output

### Integration Tests

Start from extracted student facts and verify:

- timeline evaluation runs successfully
- LangGraph state receives deterministic timeline outputs
- partial data cases still return valid timeline objects

## Implementation Notes

- Keep the timeline manager independent from the policy agent
- Keep clock calculators small and isolated
- Prefer explicit field names over opaque blobs
- Avoid embedding policy reasoning into the timeline layer

The later policy agent should read timeline outputs, not duplicate their logic.

## Open Follow-On Work

This spec intentionally leaves for later:

- user-driven event updates
- richer employment change tracking
- policy-agent integration
- final compliance verdict composition
- broader workflow orchestration inside LangGraph

Those should build on the deterministic state produced here rather than replace it.
