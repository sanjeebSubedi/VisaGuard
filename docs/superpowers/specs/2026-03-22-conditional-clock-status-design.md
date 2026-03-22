# VisaGuard Design: Conditional Timeline Clock Status Semantics

## Overview

This spec fixes a timeline-status semantics problem in VisaGuard.

The current behavior is too aggressive for conditional clocks like Cap-Gap. When the system lacks Cap-Gap-specific facts, the Cap-Gap clock currently defaults to `insufficient_data`. That status then propagates into the compliance layer, which can cause an otherwise clean student state to become `UNKNOWN` or overly severe.

This is not the right semantic model for conditional clocks.

If a clock is conditional and there is no evidence that it should apply, the correct default is `not_applicable`, not `insufficient_data`.

This slice introduces a shared architectural pattern for conditional timeline clocks and migrates `cap_gap` to use it first.

## Goals

- Distinguish core clocks from conditional clocks semantically
- Add a shared helper/pattern for conditional clock status selection
- Make `cap_gap` return `not_applicable` when no explicit trigger is present
- Preserve `insufficient_data` only for triggered conditional clocks missing required data
- Prevent conditional non-applicability from poisoning the overall compliance result
- Keep the fix primarily in the timeline layer, not in the compliance synthesizer

## Non-Goals

- Reworking every timeline clock in one pass
- Changing the deterministic compliance decision matrix directly
- Adding new Cap-Gap product fields beyond the existing data model in this slice
- Building a large taxonomy framework beyond what is needed for conditional-clock semantics

## Design Principles

- Fix semantics at the source layer
- Required vs. conditional facts must behave differently
- `not_applicable` is neutral, not a warning condition
- `insufficient_data` should mean "this should apply, but we cannot finish the calculation"
- Shared patterns are better than one-off exceptions

## Core Semantics

### Core Clocks

Core clocks are always relevant to the current compliance model when their domain applies.

Examples in the current system include:

- OPT unemployment
- STEM OPT unemployment (when category/trigger says STEM applies)
- reporting windows tied to known required events
- grace period when program-end conditions are present

For these clocks, missing required facts should continue to produce:

- `insufficient_data`

### Conditional Clocks

Conditional clocks are only relevant when there is an explicit trigger indicating they should be evaluated.

For these clocks:

- no trigger -> `not_applicable`
- trigger present but required facts missing -> `insufficient_data`
- trigger present and facts available -> evaluate normally

`cap_gap` is the first clock to use this pattern.

## High-Level Architecture

Add a shared conditional-clock helper/policy used by timeline calculators.

This helper determines whether a conditional clock is:

- `not_applicable`
- `insufficient_data`
- ready for normal evaluation

The clock calculator itself should then focus on its actual date logic once applicability is established.

This keeps the architecture clean and makes it easy to reuse the same pattern for other optional clocks later.

## Cap-Gap Trigger Model

For `cap_gap`, the v1 trigger rule is:

- if no Cap-Gap-specific fact exists, the clock is `not_applicable`
- if a Cap-Gap-specific fact exists but required data is incomplete, the clock is `insufficient_data`
- if explicit Cap-Gap data exists and is sufficient, the clock evaluates normally

Initial explicit trigger examples:

- `cap_gap_end_date`
- future dedicated Cap-Gap flags if they are added later

In the current implementation, `cap_gap_end_date` is the immediate trigger source.

## Component Breakdown

### Conditional Clock Helper

A shared helper should encapsulate the decision pattern for conditional clocks.

Responsibilities:

- inspect trigger fields
- determine whether the clock is applicable at all
- distinguish:
  - no trigger
  - trigger present but incomplete
  - ready to evaluate

### Cap-Gap Calculator

The Cap-Gap calculator should:

1. ask the shared helper whether Cap-Gap is applicable
2. return `not_applicable` when no trigger exists
3. return `insufficient_data` when the trigger exists but required values are missing
4. perform the current date arithmetic only when evaluation is warranted

### Timeline Evaluator

The timeline evaluator can remain largely unchanged if clocks emit the correct statuses.

### Compliance Normalizer

The compliance normalizer should treat `not_applicable` as neutral.

The existing logic should no longer treat a conditional clock as evidence of timeline uncertainty when that clock is simply irrelevant.

If needed, the timeline-unknown logic may be tightened so that only materially required `insufficient_data` clocks affect the aggregate unknown state.

## Data Flow

1. the timeline evaluator calls each clock calculator
2. the conditional helper checks whether a conditional clock has an explicit trigger
3. if no trigger exists, that clock returns `not_applicable`
4. if a trigger exists but triggered data is incomplete, the clock returns `insufficient_data`
5. if triggered data is complete, the clock evaluates normally
6. downstream compliance normalization sees `not_applicable` as neutral instead of missing evidence

This preserves the current flow while correcting the meaning of missing optional data.

## Error Handling

### No Trigger Present

For conditional clocks, absence of a trigger is not an error and not a missing-data condition.

The clock should return:

- `status = not_applicable`

### Trigger Present but Incomplete Data

If a conditional clock is triggered but cannot be evaluated because required triggered facts are missing, the clock should return:

- `status = insufficient_data`
- `missing_prerequisites = [...]`

### Invalid Triggered Values

If triggered date values are malformed or contradictory, the clock should fail clearly through the existing invalid-input path rather than being downgraded to `not_applicable`.

## Testing Strategy

### Unit Tests

Add or update tests for `cap_gap` covering:

- no trigger -> `not_applicable`
- trigger but missing required data -> `insufficient_data`
- valid explicit Cap-Gap end date -> active/completed behavior unchanged

### Shared Helper Tests

Add direct tests for the shared conditional-clock helper covering:

- no trigger
- trigger present but incomplete
- trigger present and sufficient

### Compliance / Normalizer Tests

Add tests proving that:

- `not_applicable` conditional clocks do not force `timeline_unknown`
- a clean OPT case can remain `IN_STATUS` when Cap-Gap is absent

### Regression Coverage

Verify:

- existing core-clock `insufficient_data` behavior remains intact
- Cap-Gap no longer degrades unrelated compliant cases
- compliance severity and overall state improve only because timeline semantics are corrected

## Rollout Notes

This slice establishes the architectural pattern for optional/conditional clocks.

After `cap_gap`, the same pattern can be reused for future clocks whose applicability depends on explicit triggers rather than being globally required.

