# VisaGuard Design: Compliance Agent

## Overview

This spec defines the final deterministic synthesis layer for VisaGuard.

The current system already:

- accepts `i20`, `ead`, and `offer_letter` uploads
- stores encrypted originals
- parses documents with Docling
- extracts normalized facts with local Ollama-based prompts
- assembles a `student_state_snapshot`
- computes deterministic `timeline_inputs` and `timeline_status`
- produces grounded `policy_analysis` and `policy_verdict`

The final missing layer is a deterministic compliance agent that combines the timeline axis and the policy axis into one definitive, frontend-ready compliance result.

This agent does not re-interpret raw documents or extracted facts. It consumes only the structured outputs of the Timeline Manager and the Policy Agent and produces a single strictly typed `final_compliance_record`.

## Goals

- Build a deterministic final synthesizer, not an LLM-based compliance judge
- Read only:
  - `timeline_status`
  - `policy_verdict`
- Normalize the two upstream outputs into internal deterministic evaluation flags
- Apply a pessimistic, fail-safe decision matrix
- Produce one strictly typed `final_compliance_record`
- Keep the result frontend-ready and directly usable in UI state
- Preserve concise, human-readable reasoning through `audit_summary`
- Reuse deterministic timeline actions where appropriate and add policy/compliance actions when needed

## Non-Goals

- Reading raw extracted facts, original documents, or retained text
- Re-running timeline calculations
- Re-running policy retrieval or semantic reasoning
- Using an LLM to draft the final result
- Replacing the Timeline Manager or Policy Agent as sources of truth
- Building a generic policy rules engine beyond this final synthesis layer

## Design Principles

- Deterministic before expressive
- Pessimistic evaluation / fail-safe composition
- Strict separation of legal axes
- No hidden inference from raw data
- Stable typed outputs for frontend use
- Small, auditable rule composition

## High-Level Architecture

The compliance agent sits after the Timeline Manager and Policy Agent.

The flow is:

1. the Timeline Manager writes `timeline_status`
2. the Policy Agent writes `policy_verdict`
3. the Compliance Agent reads those two structured outputs only
4. it normalizes them into internal deterministic pass/fail/unknown-style flags
5. it applies an ordered decision matrix
6. it computes:
   - `overall_state`
   - `severity`
   - `action_plan`
   - `audit_summary`
7. it writes the final `final_compliance_record` into LangGraph state

This keeps the final layer simple, conservative, and auditable.

## LangGraph State Contract

### Inputs

The Compliance Agent reads only:

- `timeline_status`
- `policy_verdict`

It must not read:

- raw extracted facts
- original document contents
- retained text
- raw LLM outputs
- user profile fields directly

### Output

The Compliance Agent writes one final object:

- `final_compliance_record`

### `final_compliance_record`

The output must be a strictly typed JSON-compatible object with exactly these fields:

- `overall_state`
- `severity`
- `action_plan`
- `audit_summary`

#### `overall_state`

`overall_state` is the definitive legal standing.

Initial supported enum values:

- `IN_STATUS`
- `OUT_OF_STATUS`
- `GRACE_PERIOD`
- `CAP_GAP`
- `UNKNOWN`

#### `severity`

`severity` is the frontend traffic-light urgency level.

Initial supported enum values:

- `INFO`
- `WARNING`
- `CRITICAL`
- `VIOLATION`

#### `action_plan`

`action_plan` is a prioritized list of deterministic next steps.

Examples:

- `Report employer to SEVP by 2026-06-25`
- `Contact DSO immediately regarding job duties`
- `Resolve missing policy evidence before relying on employment`

#### `audit_summary`

`audit_summary` is a concise human-readable rationale combining:

- the timeline math and status
- the policy verdict and justification

Examples:

- `85 days of unemployment used; job is directly related to Computer Science.`
- `In grace period through 2026-08-29; policy evidence is insufficient to confirm job relevance.`
- `Employment is not directly related to the major; final status is out of status.`

## Core Decision Model

The Compliance Agent evaluates two separate legal axes:

- time/status legality from `timeline_status`
- job relevance legality from `policy_verdict`

These axes do not disagree in the architectural sense. They represent independent legal conditions that must both pass.

The Compliance Agent therefore acts as a strict AND gate with pessimistic evaluation:

- both axes must pass for the student to remain compliant
- the worst legally relevant condition controls the final outcome

## Internal Normalization Layer

Before computing the final result, the Compliance Agent should normalize upstream outputs into internal flags.

### Timeline-Derived Internal Signals

Examples:

- `timeline_passes`
- `timeline_violation`
- `timeline_warning_active`
- `timeline_grace_period_active`
- `timeline_cap_gap_active`
- `timeline_unknown`

### Policy-Derived Internal Signals

Examples:

- `policy_passes`
- `policy_fails`
- `policy_unclear`
- `policy_unknown`

This normalization step is internal only. The public output remains the single `final_compliance_record`.

## Ordered Decision Matrix

The final decision should be evaluated in strict worst-case-first order.

### Rule 1: Timeline Violation Wins Immediately

If the timeline axis indicates the student is already out of status, then:

- `overall_state = OUT_OF_STATUS`
- `severity = VIOLATION`

This remains true even if the policy axis would otherwise pass.

### Rule 2: Policy Failure Produces Out-of-Status

If the policy verdict is `not_directly_related`, then:

- `overall_state = OUT_OF_STATUS`
- `severity = VIOLATION`

This remains true even if the timeline axis otherwise passes.

### Rule 3: Grace Period Applies Only When Not Overridden by Failure

If the student is in a valid grace-period state and there is no higher-severity violation, then:

- `overall_state = GRACE_PERIOD`
- `severity` should reflect whether the grace period is still normal, nearing expiry, or otherwise risky

### Rule 4: Cap-Gap Applies Only When Not Overridden by Failure

If the student is in a valid Cap-Gap state and there is no higher-severity violation, then:

- `overall_state = CAP_GAP`
- `severity` should reflect any associated risks or deadlines

### Rule 5: In-Status Requires Both Axes to Pass

If:

- the timeline axis passes, and
- the policy verdict is `directly_related`

then:

- `overall_state = IN_STATUS`

If there are active timeline risks, the severity may still be `WARNING`.
If there are no active risks, severity should be `INFO`.

### Rule 6: Incomplete Evidence Yields Unknown Unless a Definite Violation Exists

If either upstream source is incomplete:

- `timeline_status` is insufficient/malformed, or
- `policy_verdict` is `insufficient_policy_evidence`, missing, or malformed

and there is no definite violation already established, then:

- `overall_state = UNKNOWN`

This keeps the result conservative without falsely escalating to a violation when the real issue is missing evidence.

## Severity Mapping

The severity layer should be deterministic and frontend-oriented.

### `VIOLATION`

Use when any deterministic rule establishes an active out-of-status condition.

Examples:

- unemployment limit exceeded
- policy verdict `not_directly_related`
- any other explicit upstream hard-failure condition

### `CRITICAL`

Use when the student is not yet definitively out of status but immediate action is required to avoid likely violation.

Examples:

- a near-term deadline or threshold is at immediate risk
- a grace period or Cap-Gap window is ending very soon

### `WARNING`

Use when the student is still in status but has meaningful active risk or unresolved evidence.

Examples:

- approaching unemployment or reporting threshold
- `policy_verdict = unclear`
- `overall_state = UNKNOWN` due to missing evidence but no confirmed violation

### `INFO`

Use only when:

- timeline status clearly passes
- policy verdict is `directly_related`
- no material active risks are present

## Action Plan Composition

The Compliance Agent should produce a final prioritized deterministic `action_plan`.

### Timeline Actions

It should reuse and preserve Timeline Manager actions where possible.

Examples:

- report deadlines
- limit warnings
- grace-period reminders

### Policy / Compliance Actions

It should add deterministic policy/compliance actions when needed.

Examples:

- contact DSO regarding job relevance
- resolve missing policy evidence
- review role duties against major before continuing employment

### Prioritization Rules

Priority should be worst-case-first:

1. actions needed to prevent or address active violation
2. actions needed to resolve immediate legal uncertainty
3. actions tied to near-term deadlines
4. informational actions

## Audit Summary Construction

The `audit_summary` must be deterministic and composed from structured upstream data, not generated by an LLM.

It should combine:

- the decisive timeline fact or status
- the decisive policy fact or verdict
- the final state conclusion

Examples:

- `85 days of unemployment used; job is directly related to the student's major; currently in status with warning-level risk.`
- `Grace period active through 2026-08-29; policy evidence is insufficient; final status is unknown pending more evidence.`
- `Job duties are not directly related to the major; final status is out of status regardless of timeline compliance.`

## Core Components

### Compliance Normalizer

Responsibilities:

- read `timeline_status` and `policy_verdict`
- derive internal deterministic flags
- isolate the rest of the system from upstream representation details

### Decision Matrix Evaluator

Responsibilities:

- apply the ordered pessimistic rules
- compute `overall_state`
- ensure worst-case conditions dominate the result

### Severity Mapper

Responsibilities:

- derive the frontend traffic-light severity
- translate deterministic legal risk into UI urgency

### Action Plan Composer

Responsibilities:

- reuse upstream timeline actions when available
- add deterministic policy/compliance actions
- produce a single ordered `action_plan`

### Audit Summary Builder

Responsibilities:

- compose a concise human-readable explanation
- reflect the actual deterministic basis of the final result
- avoid any free-form LLM generation

### State Writer

Responsibilities:

- write `final_compliance_record` into LangGraph state
- preserve a stable frontend-facing contract

## Error Handling

### Missing Timeline Input

If `timeline_status` is missing or malformed and there is no explicit hard-failure condition elsewhere, then:

- `overall_state = UNKNOWN`
- severity should remain conservative
- action plan should prioritize resolving the missing timeline evidence

### Missing Policy Input

If `policy_verdict` is missing, malformed, or `insufficient_policy_evidence` and there is no explicit hard-failure condition elsewhere, then:

- `overall_state = UNKNOWN`
- severity should remain conservative
- action plan should prioritize resolving the missing policy evidence

### Hard Failure Dominance

If a hard-failure condition exists in either axis, that condition controls the final result even if the other input is missing or favorable.

### Missing Upstream Actions

If timeline actions are absent, the Compliance Agent should still emit a valid `final_compliance_record` using whatever deterministic compliance actions it can construct.

## Testing Strategy

### Unit Tests

Add unit tests for:

- normalization of `timeline_status` into internal timeline flags
- normalization of `policy_verdict` into internal policy flags
- decision-matrix cases based on the approved truth table
- severity mapping for `INFO`, `WARNING`, `CRITICAL`, `VIOLATION`
- action-plan composition
- deterministic `audit_summary` construction

### Required Decision Matrix Cases

At minimum, test:

- timeline violation + policy pass -> `OUT_OF_STATUS`, `VIOLATION`
- timeline pass + policy failure -> `OUT_OF_STATUS`, `VIOLATION`
- timeline warning + policy pass -> `IN_STATUS`, `WARNING`
- timeline pass + policy pass + no active risk -> `IN_STATUS`, `INFO`
- grace period active + policy pass -> `GRACE_PERIOD`
- Cap-Gap active + policy pass -> `CAP_GAP`
- timeline insufficient + policy pass -> `UNKNOWN`
- timeline pass + insufficient policy evidence -> `UNKNOWN`

### Integration Tests

Add integration tests that start from realistic `timeline_status` and `policy_verdict` objects and verify:

- `final_compliance_record` is written into LangGraph state
- the output is strictly shaped as expected
- the decision matrix behaves consistently across representative scenarios

## Relationship to the Frontend

The final output is intentionally frontend-ready.

The UI should not need to reconstruct legal meaning from lower-level signals. Instead, it should be able to read one object:

- `final_compliance_record`

and render:

- the final legal state
- the urgency color/level
- the next steps
- the concise explanation

This keeps frontend logic simple and prevents duplicated legal interpretation in the client.

## Relationship to Future Work

This spec completes the first end-to-end compliance reasoning chain:

- intake/extraction
- timeline manager
- policy agent
- final compliance agent

Future work may expand:

- more timeline clocks
- richer policy corpora
- additional compliance states or action types
- advisor/DSO escalation flows

But the final synthesis contract should remain stable: one deterministic typed record that represents the student's current compliance posture.
