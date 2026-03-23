# VisaGuard Design: Conversational DSO Agent

## Overview

This spec defines the first version of the student-facing DSO Copilot.

The current VisaGuard system already evaluates a student's documents and produces a structured compliance result through:

- the Timeline Manager
- the Policy Agent
- the Compliance Agent
- the LangGraph compliance workflow

What is still missing is a safe conversational layer that helps students understand those results, ask policy questions, and find school-specific procedural guidance without forcing human DSOs to answer every routine question.

This slice introduces a separate LangGraph conversational RAG workflow that:

- answers student questions asynchronously
- reads the student's latest workflow/compliance state fresh on every turn
- retrieves from curated federal and university knowledge bases
- supports both personalized questions and hypotheticals
- returns a structured response suitable for the chat UI
- enforces legal-tech guardrails around grounding, escalation, and date/math reasoning

## Goals

- Build a separate DSO agent workflow, not an extension of the compliance workflow
- Accept chat input as:
  - `user_id`
  - `message`
  - recent `chat_history`
- Load the latest student state fresh on every turn
- Support three broad question classes:
  - personalized status questions
  - general policy hypotheticals
  - school procedure questions
- Use curated markdown-based corpora for federal and university guidance
- Use ChromaDB with hybrid retrieval
- Return a structured response contract for the frontend
- Enforce no-math, high-risk escalation, and grounded-citation rules

## Non-Goals

- Replacing the existing evaluation engine
- Recalculating timelines or policy verdicts inside chat
- Letting the LLM perform date arithmetic on the fly
- Supporting multi-university population in this first slice
- Handling document uploads through chat in this slice
- Adding long-term conversational memory beyond recent `chat_history`
- Building an internal DSO/admin console in this slice

## Design Principles

- Read student state as immutable grounding, not editable chat context
- Prefer grounded retrieval over free-form explanation
- Separate federal guidance from university procedure guidance
- Answer hypotheticals carefully without losing personalization when relevant
- Keep the chat workflow explicit and inspectable
- Fail safely when grounding is weak

## High-Level Architecture

The DSO Copilot is a separate LangGraph application that runs in parallel to the evaluation engine and shares the same application database.

### Read-Only Context Triad

Each turn is grounded in three sources of truth:

1. **Student mathematical reality** from the app database:
   - latest `final_compliance_record`
   - latest `timeline_status`
   - latest `policy_verdict`
   - latest workflow/snapshot metadata needed for context
2. **Federal knowledge base** in ChromaDB:
   - curated eCFR/F-1/OPT/STEM guidance
   - curated SEVP guidance
   - curated USCIS policy excerpts where relevant
   - CIP code definitions
3. **University knowledge base** in ChromaDB:
   - curated markdown handbook/process documents for one university in v1
   - tagged for later `university_id` filtering, even if only one school is loaded initially

The student state is loaded directly from the app DB, not vectorized.

### Graph Shape

The conversational graph for v1 should have four main nodes:

1. `state_loader`
2. `intent_router`
3. `context_retriever`
4. `synthesizer`

The flow is sequential for a single turn, but each node has a narrow responsibility.

## Input Contract

Each chat turn should accept:

- `user_id`
- `message`
- `chat_history`

`chat_history` should be recent-turn context only. The system should not rely on hidden long-term memory in this slice.

## Student State Loading

The `state_loader` should read the student's latest saved workflow result and any lightweight profile metadata needed for retrieval filtering, such as:

- `university_id`
- latest `timeline_status`
- latest `policy_verdict`
- latest `final_compliance_record`

If the student state cannot be loaded, the request should fail clearly rather than improvising a personalized answer.

## Knowledge Base Design

### Federal Corpus

The federal corpus should be stored as curated markdown/text documents in the repo or a controlled local data directory.

Recommended source classes:

- eCFR sections relevant to F-1, OPT, STEM OPT, Cap-Gap, grace periods, and reporting
- SEVP policy and operational guidance relevant to student questions
- USCIS policy/manual excerpts only where they add clear value
- CIP code descriptions/definitions for major-related questions

### University Corpus

The university corpus should also be curated markdown/text, not raw scraped PDFs in this slice.

Recommended source classes:

- OPT application process guides
- STEM OPT process guides
- I-983 guidance
- travel signature / travel-on-OPT pages
- employer reporting and address update procedures
- school-specific forms, portals, contact pages, and escalation instructions
- school FAQ content

### Metadata Model

Each chunk should carry metadata sufficient for filtering and citation, such as:

- `source_type` (`federal`, `university`, `cip`)
- `title`
- `citation`
- `topic`
- `university_id` (for university docs)
- source path / stable document identifier

## Retrieval Strategy

The DSO agent should use hybrid retrieval:

- vector retrieval through ChromaDB
- lexical retrieval / reranking for exact-phrase matching

Hybrid retrieval is important because student questions often mix exact institutional terms (for example, `travel signature`) with fuzzy natural-language intent.

The retriever should support at least three scopes:

- federal only
- university only
- mixed retrieval

Scope should be selected based on the routed intent.

## Intent Routing

The `intent_router` should classify each turn into a small set of safe operational modes:

- `personalized_status`
- `general_policy`
- `school_procedure`
- `escalation_sensitive`

The router does not answer the question itself. It only decides what kind of evidence and answer style are needed.

### Routing Guidance

- Personalized questions should prioritize student-state grounding and may also retrieve federal guidance.
- General hypotheticals should lead with federal guidance, then optionally add a short personalized note if the student's state materially changes the practical advice.
- School procedure questions should prioritize university corpus retrieval and may supplement with federal guidance if needed.
- High-risk questions should bias toward escalation-sensitive handling.

## Synthesis Rules

The synthesizer should be Gemini-based and return a structured response.

### Response Contract

The response should include at least:

- `answer`
- `citations`
- `confidence`
- `needs_human_escalation`
- `answer_mode`

Recommended `answer_mode` values:

- `personalized`
- `general_policy`
- `school_procedure`
- `cautious_fallback`

### Answer Style

- For hypotheticals, answer the general rule first.
- If the student's current state materially changes the practical advice, add a short personalized note afterward.
- Never let the personalized note replace the cited policy basis.
- Prefer calm, plain English over legalistic phrasing.

## Guardrails

### No Math Rule

The DSO agent must not calculate dates, windows, or countdowns on its own.

If asked about time-based compliance, it may only quote or paraphrase numbers already computed by the Timeline Manager or latest workflow result.

### High-Risk Escalation

When the student appears to be out of status, near a severe violation, or asking a high-risk legal question, the response must append mandatory hardcoded escalation language advising the student to contact a human DSO or immigration attorney.

### Grounding Rule

The agent must not fabricate citations or pretend certainty when retrieval is weak.

If grounding is weak, it should return a cautious fallback answer that:

- states the uncertainty
- cites whatever relevant guidance was found
- recommends human follow-up when appropriate

## API Contract

A dedicated chat endpoint should be added for the DSO agent.

Initial shape:

- `POST /api/dso/chat`

Request body:

- `user_id`
- `message`
- `chat_history`

Response body:

- structured DSO response object

This endpoint should not modify student state. It is a read-only advisory surface.

## Persistence Model

This slice does not require long-term chat memory.

The system may log request/response traces for debugging and audit, but the core design should treat each turn as fresh, using only:

- current `message`
- recent `chat_history`
- latest loaded student state
- retrieved corpus context

If trace persistence is added, it should be separate from the canonical compliance data.

## Error Handling

### Missing Student State

If the latest workflow/student state cannot be found for `user_id`, the endpoint should fail clearly. It must not produce a personalized answer without state.

### Weak Retrieval

If retrieval is too weak to support a confident grounded answer, the agent should return a cautious fallback rather than bluffing.

### Missing University Match

If no university-specific procedure content is found, the agent may still answer from federal guidance, but it should say that school-specific steps may differ and recommend checking with the DSO.

### Malformed Gemini Output

If Gemini returns malformed structured output, the request should fail fast rather than returning an unsafe answer.

## Testing Strategy

### Unit Tests

Add focused tests for:

- intent routing
- retrieval scope selection
- guardrail decisions
- structured response validation
- escalation-language insertion

### Retrieval Tests

Seed a small Chroma test corpus and verify:

- federal-only retrieval works
- university-only retrieval works
- mixed retrieval works
- university filtering behaves correctly

### Integration Tests

Add end-to-end tests that:

- load realistic student state
- seed a small curated corpus
- ask representative questions in each mode
- verify grounded structured responses and citations

Representative questions should include:

- "How many unemployment days do I have left?"
- "Can I work two jobs on OPT?"
- "How do I get a travel signature?"
- a high-risk question that requires escalation language

## Implementation Notes

Useful earlier references exist in older branches, but they should be treated as patterns rather than direct implementations:

- `current:app/services/policy_agent.py` for ChromaDB/hybrid retrieval ideas
- `poc:app/graph/nodes/policy_agent.py` for earlier corpus/query flow
- `poc:scripts/seed_regulations.py` for seed-data structure
- `poc:app/graph/nodes/dso_agent.py` is not the target design; it was a form-generation agent, not a conversational student copilot

## Open Questions Deferred

These are intentionally deferred beyond this slice:

- chat-triggered document upload routing into the evaluation engine
- multi-university corpus population and filtering at scale
- long-term memory and conversation persistence
- internal DSO/admin review tooling
- proactive outbound messages or alerts
