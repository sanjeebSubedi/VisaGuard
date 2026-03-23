# Student Frontend Dashboard Design

## Summary

Build a student-facing React frontend for VisaGuard using Vite. The first version should let a student:

- view their current compliance result
- inspect the reasoning surfaces that matter most
- upload required documents
- manually enter EAD details
- trigger the compliance workflow
- see a persistent but explicitly disabled DSO Copilot sidebar that will later become the conversational DSO agent surface

This frontend is intentionally designed around the future DSO agent, but the DSO agent itself is not part of this implementation slice.

## Goals

- Create a trustworthy student-facing dashboard centered on compliance clarity
- Expose the existing backend intake and workflow APIs through a usable UI
- Reduce anxiety by making status, action items, and clock math easy to understand
- Build the app shell and layout in a way that can absorb the future DSO chat agent without major redesign

## Non-Goals

- Authentication or role-based access control
- A functioning chat backend or DSO agent
- New compliance logic in the frontend
- Replacing backend evaluation with frontend calculations
- Admin or internal DSO console surfaces

## Product Shape

The first frontend release is a student application with two routes:

- `/` - dashboard
- `/intake` - document upload and manual EAD entry

The app uses a temporary dev-mode `user_id` selector rather than auth.

## Core UX Principles

### 1. Verdict First
The first thing a student should see is the current legal/compliance state, not raw data.

### 2. Actionability Over Exhaustiveness
When action is required, the UI should immediately show what the student needs to do next.

### 3. Trust Through Transparency
The dashboard should show the relevant clock math so the system does not feel like a black box.

### 4. DSO Agent Readiness
The chat sidebar should already exist in the layout, but be explicitly disabled and labeled as coming soon.

## Layout

The application shell uses a two-column desktop layout:

- left: primary content area
- right: persistent sticky DSO Copilot sidebar

### Left Content Area

#### Zone 1: Traffic Light Hero Card
This is the focal point of the dashboard.

Data source:
- `final_compliance_record.overall_state`
- `final_compliance_record.severity`
- `final_compliance_record.audit_summary`

Behavior:
- background and accent color are derived from `severity`
- primary headline shows the overall state in large typography
- supporting paragraph shows the audit summary in plain English

Color mapping:
- `INFO` -> green
- `WARNING` -> amber/yellow
- `CRITICAL` -> red
- `VIOLATION` -> deeper red/crimson

#### Zone 2: Action Center
This sits directly below the hero card.

Data source:
- `final_compliance_record.action_plan`

Behavior:
- render checklist-style action items when present
- if empty, either hide the card entirely or show a reassuring empty state such as “All caught up! No actions required at this time.”

#### Zone 3: Compliance Clocks
This is where the student sees the math.

Primary data source:
- `timeline_status.clocks`

Rendering rules:
- render only clocks with `status == active`
- hide `not_applicable`
- usually hide `completed`
- only show `insufficient_data` when it materially affects the student and should be visible as a lightweight warning row

For each active clock, show:
- a human-friendly clock label
- a progress bar
- a label like `38 of 90 days used (52 days remaining)`

Progress math:
- `(limit_days - days_remaining) / limit_days` for used amount

#### Zone 4: Document and Workflow Summary
A compact supporting section on the dashboard should show:
- current document presence/status for I-20, EAD, and offer letter
- whether a latest workflow result exists
- workflow freshness or last evaluation date if available
- quick links/actions to go to intake or rerun the workflow

### Right Content Area: DSO Copilot Sidebar
The sidebar is visible in v1 but intentionally disabled.

Behavior:
- render a polished chat layout
- show a welcome/placeholder message
- input and send button are visibly disabled
- include a short explanation that the DSO Copilot is coming soon

The sidebar should look intentionally unavailable, not broken.

## Routes

### `/`
Dashboard route containing:
- hero card
- action center
- compliance clocks
- document/workflow summary
- persistent disabled chat sidebar

### `/intake`
Dedicated intake route containing:
- I-20 upload form
- offer-letter upload form
- manual EAD entry form
- success/error feedback for submissions
- an action to run or return to workflow evaluation after intake

## Frontend Stack

- React
- Vite
- React Router for routing
- Tailwind CSS for styling
- Lightweight local component primitives rather than a heavy component framework
- Thin typed API client layer for backend communication
- A client-side state/query layer for request lifecycle and caching

## Backend Integration

The frontend talks directly to the existing FastAPI backend.

### Existing APIs to use

Intake:
- `POST /api/intake/documents`
- `POST /api/intake/ead/manual`
- `GET /api/intake/users/{user_id}/snapshot`
- `GET /api/intake/users/{user_id}/review-items`

Workflow:
- `POST /api/workflows/compliance/run`

### Workflow Trigger in UI
The frontend should allow the student to trigger the compliance workflow directly.

Expected behavior:
- after upload or manual EAD entry, the user can run the workflow
- the UI shows a loading state while the workflow is in progress
- duplicate runs are prevented while a request is active
- when the response returns, the dashboard updates immediately from the returned state

## State Model in the Frontend

### App-Level Context
The app should maintain a selected `user_id` in client state.

This selected `user_id` is used for:
- loading snapshot data
- submitting intake requests
- running the compliance workflow

### Derived Dashboard Data
The dashboard is primarily driven by:
- `final_compliance_record`
- `timeline_status`
- snapshot data for extracted facts and document-level context

The frontend should not recalculate compliance decisions or dates beyond simple progress-bar display math based on backend-provided values.

## Component Model

### AppShell
Responsibilities:
- header/title
- `user_id` selector/input
- top-level layout
- route outlet
- persistent chat sidebar

### HeroStatusCard
Responsibilities:
- severity-based visual styling
- rendering `overall_state`
- rendering `audit_summary`

### ActionCenter
Responsibilities:
- render `action_plan`
- handle empty-state messaging

### ComplianceClockList
Responsibilities:
- filter visible clocks
- map clock objects to progress rows
- show labels and remaining/used values

### DocumentSummaryCard
Responsibilities:
- summarize document presence and snapshot availability
- provide shortcut CTA to intake or rerun evaluation

### IntakeForms
Responsibilities:
- upload I-20
- upload offer letter
- manual EAD entry
- show inline validation and success states

### WorkflowRunControl
Responsibilities:
- run the workflow for the selected `user_id`
- surface loading, success, and failure states

### DisabledChatSidebar
Responsibilities:
- render future DSO Copilot shell
- remain clearly disabled
- establish future spatial and product expectations

## Error Handling

### Empty State
If no snapshot or workflow result exists for the selected `user_id`, the dashboard should show a friendly empty state with a clear next step, such as going to intake.

### Submission Errors
Upload and manual EAD failures should show inline error messaging near the relevant form.

### Workflow Errors
If workflow execution fails:
- show a clear, non-technical user message in the UI
- preserve the previous visible dashboard state if present
- allow retry

### Partial Data
If some dashboard sections cannot render because data is missing:
- render known values
- explicitly label missing sections
- never crash the page

## DSO Agent Readiness Requirements

The frontend must be designed so the future DSO agent can slot into the existing sidebar without a layout rewrite.

The sidebar should later be able to support:
- chat history
- user message input
- streamed or async responses
- answer cards grounded in compliance state and policy sources
- upload-trigger handoff to the evaluation engine

For this slice, the UI only reserves that space and visual pattern.

## Testing Strategy

### Unit Tests
Cover:
- severity rendering for the hero card
- action center empty and non-empty states
- active clock filtering and progress calculations
- disabled chat sidebar behavior

### API Client Tests
Cover:
- document upload request formatting
- manual EAD request formatting
- workflow-run request formatting
- response/error parsing

### Page Tests
Cover:
- dashboard empty state
- dashboard renders workflow results correctly
- intake success and error flows
- disabled workflow button while request is running

### End-to-End Happy Path
A lightweight full-flow test should cover:
- selecting a `user_id`
- completing intake actions
- running the workflow
- seeing the updated hero card, action items, and active clocks

## Rollout Recommendation

Implement the frontend in this order:
1. scaffold the Vite React app and shared shell
2. add routing and `user_id` selection
3. build dashboard components with mocked typed data
4. wire in real workflow API calls
5. build intake forms and connect intake APIs
6. finish empty/error/loading states
7. add tests and polish

## Success Criteria

The frontend slice is successful when a student can:
- enter/select a `user_id`
- upload an I-20 and offer letter
- manually enter EAD details
- trigger the workflow
- see `overall_state`, `severity`, `action_plan`, and `audit_summary`
- inspect active compliance clocks visually
- understand that the DSO Copilot exists but is not yet enabled
