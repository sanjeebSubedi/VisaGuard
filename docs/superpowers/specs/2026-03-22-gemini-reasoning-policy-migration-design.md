# VisaGuard Design: Gemini Reasoning Migration for Policy Agent

## Overview

This spec corrects the LLM boundary for VisaGuard.

The intended architecture is:

- local open-source model (`Ollama`) for document ingestion only
- stronger hosted reasoning model (`Gemini`) for non-ingestion reasoning
- deterministic services for timeline and compliance synthesis

The current implementation on `restart` still uses the local Ollama model inside the policy agent. In practice, that has proven too brittle for the structured policy-analysis and policy-verdict outputs required by the workflow. A malformed local-model verdict response can currently crash the workflow.

This slice migrates the policy agent to Gemini through a shared reasoning-LLM adapter while leaving ingestion on Ollama and leaving timeline/compliance deterministic.

## Goals

- Keep `Ollama` limited to document ingestion
- Introduce a shared Gemini-based adapter for non-ingestion reasoning
- Move the policy agent to that Gemini adapter
- Preserve the current policy-agent retrieval pipeline and structured outputs
- Keep the LangGraph workflow shape unchanged
- Split configuration clearly between ingestion and reasoning models
- Fail fast when Gemini is unavailable or returns malformed structured output

## Non-Goals

- Replacing the ingestion LLM path
- Moving timeline logic to an LLM
- Moving compliance synthesis to an LLM
- Building a fully generalized multi-provider framework
- Adding repair/retry loops for malformed Gemini policy responses in this slice

## Design Principles

- Correct model boundary over convenience
- Hosted reasoning for higher-order policy tasks
- Local model only where cost/privacy/latency justify it
- Deterministic services remain deterministic
- Fail fast rather than silently downgrading policy reasoning
- Shared adapter boundary for future non-ingestion reasoning reuse

## High-Level Architecture

### LLM Boundary After Migration

#### Ingestion LLM Path

Document ingestion continues to use:

- Docling for parsing
- Ollama for extraction

This includes:

- `i20` extraction
- `ead` extraction
- `offer_letter` extraction

#### Non-Ingestion Reasoning LLM Path

Policy reasoning moves to Gemini through a shared adapter.

This path is for:

- policy analysis generation
- policy verdict generation
- future non-ingestion reasoning tasks

#### Deterministic Services

The following remain non-LLM:

- Timeline Manager
- Compliance Agent

## Component Breakdown

### Gemini Reasoning Adapter

Add a thin shared adapter around the official Google GenAI Python SDK.

Responsibilities:

- initialize Gemini client
- accept model name and prompt/input payload
- request structured output
- return parsed structured data or raise a clear error

This adapter should not own policy logic. It only handles provider interaction.

### Policy Agent Integration

The policy agent keeps its current high-level flow:

1. load CIP entry
2. retrieve CIP + policy evidence
3. build analysis prompt
4. ask reasoning adapter for structured policy analysis
5. build verdict prompt
6. ask reasoning adapter for structured policy verdict
7. validate/store typed outputs

The migration changes only the provider boundary for steps 4 and 6.

### Workflow Integration

The LangGraph workflow remains structurally unchanged.

The workflow service should now construct the policy agent with:

- Gemini reasoning adapter
- Gemini model name

The workflow still:

- fans out to timeline and policy
- fans in to compliance
- persists latest workflow outputs

### Configuration Layer

Configuration should clearly separate ingestion and reasoning models.

Recommended settings:

- `OLLAMA_MODEL` for document ingestion
- `GEMINI_MODEL` for non-ingestion reasoning
- `GEMINI_API_KEY` (environment)

Optional future Gemini tuning fields may be added later, but are not required for this slice.

## Data Flow

1. document ingestion runs exactly as it does today using Ollama
2. snapshot data is loaded into the workflow
3. the policy agent retrieves relevant CIP/policy evidence
4. the policy agent calls Gemini through the reasoning adapter for structured analysis output
5. the policy agent calls Gemini through the reasoning adapter for structured verdict output
6. the policy agent writes `policy_analysis` and `policy_verdict`
7. timeline and compliance continue unchanged

This keeps the non-ingestion reasoning upgrade isolated to the policy layer.

## Structured Output Contract

Gemini should be asked for structured outputs that match the existing policy-agent models.

### Policy Analysis Output

Must still match:

- `summary`
- `evidence_strength`
- `ambiguity_notes`

### Policy Verdict Output

Must still match:

- `verdict`
- `confidence`
- `rationale`
- `cited_source_ids`

Where `rationale` is a structured object containing:

- `major_match`
- `duty_match`
- `policy_basis`
- `summary`

The policy agent should validate Gemini output against these expected structures before constructing typed models.

## Error Handling

### Gemini Unavailable

If Gemini is unavailable or authentication fails:

- the policy agent fails immediately
- the workflow request fails immediately

### Malformed Structured Output

If Gemini returns malformed structured output:

- the policy agent fails immediately
- the workflow request fails immediately

This slice does not add a repair loop.

### Schema Mismatch

If Gemini returns valid JSON that does not conform to the expected policy schema:

- the policy agent fails immediately
- the workflow request fails immediately

### Retrieval Failures

Existing retrieval/index-loading failures remain unchanged and should still fail clearly.

## API / Workflow Impact

No new API surface is required for this migration.

Existing behavior changes are internal:

- `/api/intake/*` remains Ollama-backed for extraction
- `/api/workflows/compliance/run` now uses Gemini indirectly through the policy agent

This means the workflow endpoint becomes more reliable for policy reasoning without changing its request/response contract.

## Testing Strategy

### Unit Tests

- Gemini adapter returns structured content for valid stub responses
- Gemini adapter raises clear errors for provider failures
- policy-agent tests use Gemini adapter stubs instead of Ollama stubs
- policy-agent tests verify typed analysis/verdict construction still works

### Failure-Path Tests

- missing Gemini API key
- Gemini unavailable
- malformed structured response
- structured response with wrong schema shape

### Integration Tests

- workflow integration still writes `policy_analysis` and `policy_verdict`
- workflow endpoint still returns `final_compliance_record`
- ingestion tests continue to prove Ollama-backed extraction remains unchanged

### Regression Coverage

- ingestion still uses `Ollama`
- policy agent no longer depends on the Ollama client
- timeline remains deterministic
- compliance remains deterministic

## Rollout Notes

This migration is intentionally scoped to the policy agent because that is the current non-ingestion reasoning layer.

After this migration, future non-ingestion reasoning features should reuse the Gemini reasoning adapter rather than introducing new direct provider calls.

