# VisaGuard Design: LangGraph Workflow Orchestration

## Overview

This spec defines the first callable LangGraph workflow for VisaGuard.

The current system already has the three core evaluators needed for end-to-end compliance reasoning:

- the Timeline Manager
- the Policy Agent
- the Compliance Agent

Each evaluator already works independently and produces structured outputs. The missing layer is a real orchestration workflow that runs those evaluators together in the correct order and exposes them through a callable service/API.

This slice introduces a LangGraph workflow that:

- loads the latest extracted student snapshot by `user_id`
- builds initial graph state from that snapshot
- runs Timeline and Policy in parallel
- waits for both to finish
- runs Compliance as the final deterministic synthesizer
- persists the latest workflow result for that user
- relies on LangGraph's built-in checkpointer for execution history and audit trail

## Goals

- Build a real LangGraph `StateGraph`, not a sequential wrapper
- Accept workflow input as:
  - `user_id`
  - optional `evaluation_date`
- Load the current student snapshot from storage before graph execution
- Keep `extracted_data` nested inside graph state
- Fan out to Timeline and Policy in parallel
- Fan in to Compliance after both upstream nodes complete
- Have each node return only its state delta
- Fail fast if either parallel branch fails
- Return the fully updated state from the API
- Persist only the latest workflow result in the app database
- Use LangGraph's checkpointer for execution history keyed by `thread_id = user_id`

## Non-Goals

- Building a sequential orchestration shim instead of a graph
- Replacing the existing evaluator implementations
- Creating a custom SQL execution-history system for every graph run
- Reading raw source documents directly inside the workflow nodes
- Supporting background execution, job polling, or async workflow management in this slice
- Introducing a full student-profile table in this slice

## Design Principles

- Real graph orchestration over fake orchestration
- Parallel where dependencies allow it
- Deterministic node behavior where already established
- Clear separation between latest product state and workflow audit trail
- Fail fast on node failure
- Delta-based state updates for clean merge behavior

## High-Level Architecture

The workflow is a LangGraph `StateGraph` over a shared VisaGuard state object.

### Initial Workflow Input

The external workflow/API layer accepts:

- `user_id`
- `evaluation_date` (optional)

The workflow service loads the latest `StudentStateSnapshot` for that `user_id` and builds the initial graph state with:

- `extracted_data`
- `evaluation_date`
- optional `user_profile` (reserved, carried through state but unused in v1)

### Graph Shape

The graph shape is:

1. entry
2. parallel fan-out to:
   - `timeline`
   - `policy`
3. fan-in to:
   - `compliance`
4. finish

### Node Responsibilities

- `timeline` reads `extracted_data` and `evaluation_date`, then returns:
  - `timeline_inputs`
  - `timeline_status`
- `policy` reads `extracted_data`, then returns:
  - `policy_analysis`
  - `policy_verdict`
- `compliance` reads:
  - `timeline_status`
  - `policy_verdict`
  and returns:
  - `final_compliance_record`

Each node returns only its delta. LangGraph merges the shared state.

## LangGraph State Contract

### Input State

The graph input state should include at least:

- `extracted_data`
- `evaluation_date`
- `user_profile` (optional, unused in v1)

`extracted_data` remains nested rather than being flattened into top-level keys.

### Derived State

During execution, the graph may accumulate:

- `timeline_inputs`
- `timeline_status`
- `policy_analysis`
- `policy_verdict`
- `final_compliance_record`

### Output State

The returned workflow state should include the initial input plus all successful node outputs.

The API should return the full updated state object, not a reduced frontend wrapper.

## Persistence Model

### Latest-State Persistence

The main app database should store only the latest workflow result per user in a narrow table.

Recommended fields:

- `user_id`
- `evaluation_date`
- `timeline_status`
- `policy_analysis`
- `policy_verdict`
- `final_compliance_record`
- timestamps

This table exists to support fast product reads and API inspection of the latest workflow result.

### Audit Trail / Execution History

Execution history should not be implemented manually through custom run-history tables.

Instead, the compiled LangGraph should use a checkpointer. The checkpointer should:

- persist full state transitions automatically
- retain execution history for each workflow run
- key workflow threads by `thread_id = user_id`

This gives the system an audit trail without complicating the main application schema.

## API Contract

### Endpoint

A workflow endpoint should be added to invoke the graph by user.

Initial shape:

- `POST /api/workflows/compliance/run`

### Request

The request should contain:

- `user_id`
- optional `evaluation_date`

### Behavior

The API should:

1. load the latest snapshot for `user_id`
2. build the initial graph state
3. run the LangGraph workflow
4. persist the latest workflow outputs
5. return the full updated state

### Response

The response should include the full workflow state, including:

- `extracted_data`
- `timeline_inputs`
- `timeline_status`
- `policy_analysis`
- `policy_verdict`
- `final_compliance_record`

## Error Handling

### Missing Snapshot

If no snapshot exists for `user_id`, the API returns a clear not-found error.

### Missing Policy Index

If the local policy index is missing, the workflow/API fails clearly. It must not auto-build the index during a request.

### Node Failure

If either parallel branch fails:

- the workflow fails immediately
- the other branch result is not treated as success for the request
- the `compliance` node does not run

### Invalid Snapshot / Adapter Failure

If the stored snapshot cannot be adapted into valid graph input state, the API fails clearly before graph execution.

### Persistence Failure

If workflow execution succeeds but latest-state persistence fails, the request fails. The system should not return a misleading success response.

## Component Breakdown

### Workflow State Adapter

Responsible for:

- loading the latest `StudentStateSnapshot`
- translating `snapshot_payload` into `extracted_data`
- attaching `evaluation_date`
- optionally carrying through `user_profile`

### Timeline Node Wrapper

Responsible for:

- reading `extracted_data`
- invoking the existing timeline evaluator
- returning only `timeline_inputs` and `timeline_status`

### Policy Node Wrapper

Responsible for:

- reading `extracted_data`
- invoking the existing policy agent
- returning only `policy_analysis` and `policy_verdict`

### Compliance Node Wrapper

Responsible for:

- reading merged upstream state
- invoking the existing compliance agent
- returning only `final_compliance_record`

### LangGraph Builder

Responsible for:

- defining the `StateGraph`
- declaring edges for parallel fan-out and fan-in
- compiling the workflow with a checkpointer

### Latest-State Persistence Layer

Responsible for:

- upserting the latest workflow result for `user_id`
- storing only the current result in the app DB

### Workflow API Route

Responsible for:

- request validation
- snapshot lookup
- graph invocation
- latest-state persistence
- response serialization

## Testing Strategy

### Unit Tests

- state adapter tests for snapshot-to-graph-state conversion
- node wrapper tests to ensure each node returns only its delta
- latest-state persistence tests
- workflow builder tests verifying graph shape and compilation

### Graph/Workflow Tests

- Timeline and Policy execute as parallel branches
- Compliance runs only after both upstream nodes succeed
- merged state contains all expected outputs
- node failure prevents compliance execution

### API Integration Tests

- successful workflow run by `user_id`
- missing snapshot returns not found
- missing policy index returns a clear failure
- latest workflow outputs are persisted after success
- response returns the full updated state

### Regression Coverage

- workflow still returns the same structured `timeline_status`
- workflow still returns the same structured `policy_verdict`
- workflow still returns the same structured `final_compliance_record`
- storage remains latest-state only while checkpointer handles execution history

## Rollout Notes

This slice creates the orchestration backbone for the full compliance system.

After this workflow exists, the next likely improvements are:

- exposing separate read endpoints for latest workflow results
- allowing the frontend to trigger recomputation by user
- improving policy retrieval quality
- expanding workflow inputs beyond document-derived facts

