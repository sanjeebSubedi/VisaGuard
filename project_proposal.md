## **VisaGuard — Privacy-Preserving, Multi-Agent Orchestration for F-1 Compliance**

### **1. Problem Statement**

International students navigate a minefield of static regulations (USCIS policies) and dynamic personal states (employment dates, OPT clocks). Current solutions are manual and error-prone. A single missed deadline leads to status violation. This is not a chatbot problem; it is a **State Management & Regulatory Reasoning** problem.

### **2. System Architecture (The "Compound AI System")**

This system is architected not as a linear chain, but as a **Cyclic State Graph** using **LangGraph**.

**Frontend:** React / Streamlit
**Backend:** FastAPI
**Orchestration:** LangGraph (State Management)
**Database:** PostgreSQL (User State) + ChromaDB (Vector Store)
**Observability:** LangSmith / Arize Phoenix

---

### **3. The Privacy Layer (Crucial Addition)**

*Before any agent sees a document, it must pass through the Privacy Gateway.*

* **Component:** **PII Scrubbing Pipeline**
* **Tooling:** **Microsoft Presidio** + Custom Regex
* **Function:** Automatically detects and redacts sensitive entities (SSN, Passport Numbers, A-Numbers) from PDFs *before* they are sent to the LLM or Vector DB.
* **Why this matters:** Ensures compliance with data privacy standards; allows use of hosted models (like GPT-4o) without leaking sensitive user data.

---

### **4. Agents & Tools (The "Brain")**

#### **1 Document Agent (The Ingestion Engine)**

* **Goal:** Convert unstructured PDFs into structured JSON schema.
* **Tooling:** **LlamaParse** (specifically for complex table extraction in I-20s).
* **Task:** Extracts `Employer Name`, `Start Date`, `EIN`, `Job Description`.
* **Engineering Note:** Uses a **Pydantic Parser** to enforce strict typing. If the LLM returns a date as "Next Monday," the parser forces a retry until it gets "YYYY-MM-DD."

#### **2 Policy Agent (The RAG Specialist)**

* **Goal:** Retrieve correct legal ground-truth.
* **Tooling:** **Hybrid Search** (Keyword + Semantic).
* **Logic:**
* *Query:* "Can I work unpaid?"
* *Retrieval:* Fetches "8 CFR 214.2(f)" (Exact Code) AND semantic matches from the University Handbook.
* **Guardrail:** If the similarity score is below 0.7, it returns "I need manual verification" rather than hallucinating a rule.



#### **3 Timeline Manager (The Deterministic Node)**

* **Goal:** Calculate deadlines with 100% mathematical precision.
* **Tooling:** Python `datetime` library + `pandas`.
* **Why:** LLMs are bad at math. This node executes code: `unemployment_days = (current_date - job_end_date).days`.
* **Output:** Precise flags (e.g., `"WARNING: 88/90 days used"`).

#### **4 Compliance Agent (The Reasoning Core)**

* **Goal:** Synthesize Document Data + Policy Rules + Timeline Math.
* **Logic:**
* *Input:* Job Description (Doc Agent) + "Must be related to major" (Policy Agent).
* *Reasoning:* "Does 'Backend Engineer' match 'Master of Science in CS'?"
* *Output:* Compliance Verdict with citations.



#### **5 DSO Agent (The Action Layer)**

* **Goal:** Draft actionable communications.
* **Output:** Pre-filled **Form I-983** (PDF generation) and draft emails to the real DSO.

---

### **6 Evaluation Strategy**

* **Golden Dataset:** A manually curated set of 50 "Edge Case" scenarios (e.g., "Student works 19 hours/week on OPT" -> Should be VIOLATION).
* **Automated Testing:**
* **Framework:** **DeepEval** or **Ragas**.
* **Metric 1 (Hallucination):** Does the cited regulation actually exist in the retrieved context?
* **Metric 2 (Reasoning):** Did the agent correctly calculate the grace period end date?


* **CI/CD:** These tests run automatically on every GitHub commit.
