# VisaGuard Design: Policy Agent

## Overview

This spec defines the first RAG-powered policy reasoning slice for VisaGuard.

The current system already:

- accepts `i20`, `ead`, and `offer_letter` uploads
- stores encrypted originals
- parses documents with Docling
- extracts normalized facts with local Ollama-based prompts
- assembles a `student_state_snapshot`
- computes deterministic `timeline_inputs` and `timeline_status`

The next missing layer is a grounded policy agent that determines whether a student's job is directly related to their field of study. This agent compares extracted job information against the student's `cip_code`, major/program context, and official DHS/SEVP policy materials. Its output becomes a structured semantic input for the final compliance agent.

## Goals

- Build a grounded policy agent, not a free-form legal chatbot
- Use RAG over local knowledge sources only in this first version
- Operate on structured student fields only:
  - `cip_code`
  - major/program info
  - job title
  - job duties
- Support local knowledge sources for:
  - CIP code descriptions
  - official DHS/SEVP policy guidance, including SEVP Policy 1004-03
- Use hybrid retrieval:
  - lexical retrieval
  - vector retrieval
- Prebuild and persist retrieval indexes locally
- Use a two-step reasoning flow:
  - policy applicability analysis
  - final structured verdict
- Write both `policy_analysis` and `policy_verdict` into LangGraph state
- Return a structured policy verdict with:
  - `verdict`
  - `confidence`
  - structured `rationale`
  - `cited_sources`
- Return `insufficient_policy_evidence` when grounding is too weak for a reliable verdict

## Non-Goals

- Building the final compliance agent in this spec
- Using retained offer-letter text in this first version
- Relying on external runtime lookups for CIP definitions or policy materials
- Making a verdict without retrieval grounding
- Supporting every DHS/SEVP source in the first iteration
- Turning the policy agent into a general immigration Q&A system

## Design Principles

- Grounded before fluent
- No invented citations
- Local, stable, and auditable knowledge sources
- Structured outputs for downstream workflow use
- Clear separation between intermediate analysis and final verdict
- Conservative fallback when evidence is weak

## High-Level Architecture

The policy agent sits after intake extraction and timeline evaluation.

The flow is:

1. intake/extraction produces structured student facts
2. the timeline manager writes deterministic timeline outputs into LangGraph state
3. the policy agent reads the structured academic/job inputs from state
4. it loads the matching CIP entry from a local JSON dataset
5. it retrieves relevant policy passages from a prebuilt local hybrid index
6. it produces a structured `policy_analysis` artifact grounded in the retrieved evidence
7. it produces a final structured `policy_verdict`
8. both artifacts are written back into LangGraph state for the later compliance agent

This keeps semantic reasoning grounded and makes the final synthesizer simpler.

## LangGraph State Contract

### Source Inputs

The policy agent reads from LangGraph state:

- `cip_code`
- extracted major/program information
- extracted `position_title`
- extracted `job_duties`
- any other normalized academic/employment facts needed to frame the comparison
- `timeline_status` may exist in state already, but it is not a primary input to this agent's verdict

### New Policy Outputs

The policy agent writes:

- `policy_analysis`
- `policy_verdict`

### `policy_analysis`

`policy_analysis` is the structured intermediate artifact produced before the final verdict.

Expected contents:

- the CIP entry used for comparison
- retrieved policy passages used for reasoning
- applicability summary describing how the job duties align or fail to align with the major/program
- evidence strength notes
- any missing evidence or ambiguity markers

This artifact is for traceability, debugging, and downstream review.

### `policy_verdict`

`policy_verdict` is the canonical semantic output for downstream workflow use.

Expected top-level shape:

- `verdict`
- `confidence`
- `rationale`
- `cited_sources`

Supported verdict values:

- `directly_related`
- `not_directly_related`
- `unclear`
- `insufficient_policy_evidence`

Supported confidence values:

- `high`
- `medium`
- `low`

### Structured Rationale

The rationale should be structured rather than free-form only.

Expected fields:

- `major_match`
- `duty_match`
- `policy_basis`
- `summary`

This keeps the output easier for the final compliance agent to consume and easier for humans to review.

## Knowledge Sources

### CIP Dataset

The first version should use a local JSON dataset mapping:

- `cip_code`
- `title`
- `description`

This dataset should be curated and versioned in the repo or in a local managed data directory.

The policy agent should not depend on external runtime CIP lookups.

### Policy Corpus

The first version should use local text or markdown policy files containing:

- SEVP Policy 1004-03
- closely related official DHS/SEVP guidance directly relevant to the "directly related" determination

These files should be chunked and indexed ahead of time.

### Retrieval Index

The retrieval layer should combine:

- lexical retrieval for exact policy/CIP phrasing
- vector retrieval for semantic similarity

The index should be built ahead of time and stored locally rather than rebuilt on every app startup.

## Core Components

### CIP Dataset Loader

Responsibilities:

- load the local CIP JSON dataset
- normalize CIP lookup behavior
- return the matching CIP title/description for the student's `cip_code`
- surface missing CIP entries explicitly

### Policy Corpus Loader / Indexer

Responsibilities:

- load local policy source files
- chunk them into retrieval-ready passages
- build and persist the hybrid retrieval index
- preserve source metadata needed for citation integrity

### Hybrid Retriever

Responsibilities:

- retrieve relevant CIP and policy evidence for the current case
- combine lexical and vector signals
- return grounded source passages with metadata
- distinguish source types so the final verdict can cite them clearly

### Policy Analysis Step

Responsibilities:

- consume the structured student inputs plus retrieved evidence
- produce a structured applicability summary
- explain how the job duties do or do not align with the student's major/program
- surface ambiguity when evidence is mixed or incomplete

This is the first reasoning step, not the final verdict.

### Policy Verdict Step

Responsibilities:

- consume the structured `policy_analysis`
- produce the final structured `policy_verdict`
- map the case into one of the supported verdict categories
- assign a `high | medium | low` confidence label
- include structured rationale and grounded citations only

### Evidence Gate

Responsibilities:

- block firm verdicts when retrieval grounding is too weak
- emit `insufficient_policy_evidence` rather than force an answer
- ensure every cited source came from retrieved local evidence

### State Writer

Responsibilities:

- write `policy_analysis` into LangGraph state
- write `policy_verdict` into LangGraph state
- preserve a stable contract for the later compliance agent

## Supported Reasoning Flow

### Step 1: Applicability Analysis

Inputs:

- student `cip_code`
- major/program info
- job title
- job duties
- matching CIP description/title
- retrieved policy passages

Outputs:

- structured analysis of whether the duties appear aligned with the field of study
- notes on ambiguity, mismatch, or strong alignment
- source-backed observations only

### Step 2: Final Verdict

Inputs:

- `policy_analysis`

Outputs:

- final `verdict`
- `confidence`
- structured `rationale`
- `cited_sources`

This separation improves traceability and makes debugging easier when verdict quality is weak.

## Error Handling

### Missing or Unknown CIP Code

If the student `cip_code` is missing or does not exist in the local dataset, the agent should not guess. It should return:

- `verdict=insufficient_policy_evidence`
- low confidence
- rationale explaining the missing CIP grounding

### Weak Retrieval

If hybrid retrieval does not return strong enough evidence, the evidence gate should block a firm verdict and return `insufficient_policy_evidence`.

### Partial Evidence

If only one source family is available, the agent may proceed only when the available evidence is clearly sufficient. Otherwise it should return `insufficient_policy_evidence`.

### Analysis/ Verdict Failure Split

If the analysis step succeeds but the verdict step fails, the system should preserve the intermediate analysis artifact for debugging and return a blocked/failure result rather than silently dropping the evidence.

### Citation Integrity

The agent must never fabricate citations. Every cited source must come from retrieved local corpus entries.

## Testing Strategy

### Unit Tests

Add unit tests for:

- CIP dataset loading and lookup
- unknown/missing `cip_code` handling
- policy corpus loading/index metadata preservation
- hybrid retriever behavior
- `policy_analysis` structured output parsing
- `policy_verdict` structured output parsing
- citation integrity

### Failure-Path Tests

Add focused tests for:

- missing CIP entry
- weak retrieval leading to `insufficient_policy_evidence`
- blocked verdict generation when grounding is inadequate
- malformed or incomplete intermediate outputs

### Integration Tests

Add integration tests that start from extracted student facts and verify:

- CIP lookup occurs correctly
- policy retrieval returns grounded source entries
- `policy_analysis` is written to LangGraph state
- `policy_verdict` is written to LangGraph state
- the final shape is stable for downstream compliance synthesis

### Regression Cases

Maintain a small set of realistic fixed cases using representative majors and job duties so prompt, retrieval, or corpus changes can be evaluated over time.

## Relationship to the Compliance Agent

This spec intentionally stops at the grounded semantic policy verdict.

The later compliance agent will consume:

- `timeline_status`
- `policy_verdict`
- potentially other workflow state artifacts

and produce the final legal/compliance synthesis.

The policy agent should therefore remain focused on one question only:

- is the job directly related to the student's field of study, based on grounded policy evidence?

That separation keeps the final compliance synthesis simpler and safer.
