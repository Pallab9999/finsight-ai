# FinSight AI
## Financial Intelligence & Decision Engine

> **Hackathon implementation document / single source of truth**
>
> **Mission:** Build a polished, working vertical slice of FinSight AI in four hours: an AI-assisted financial intelligence engine that evaluates an SME financing proposal using structured financial data, public economic data, ESG evidence, deterministic scoring, grounded retrieval, and scenario simulation.

---

## 1. Product Decision

### Product name
**FinSight AI**

### Product positioning
FinSight is a financial intelligence platform for banks and wealth-management organisations. For the hackathon, we prove the platform through one concrete workflow:

> **Assess an SME financing proposal and explain the financial risk, ESG alignment, evidence, and consequences of alternative financing scenarios.**

The long-term platform can expand into broader portfolio intelligence, forecasting, monitoring, and wealth-management workflows. The hackathon build must **not** attempt to implement the entire platform.

### The hackathon vertical slice

**User:** Bank relationship manager / SME credit officer

**Example applicant:** EcoTex Milano

**Example request:** €750,000 for energy-efficient / water-recycling manufacturing equipment

**Core output:**
- Financial Health Score
- ESG Alignment Score
- Regional Risk
- Sector Outlook
- Overall Assessment
- Evidence / sources
- Explainable decision factors
- One what-if financing scenario

### One-line pitch

> **FinSight turns fragmented financial data into explainable, evidence-backed financing intelligence—showing a bank not only the risk of an SME loan, but why the decision changes under different scenarios.**

---

# 2. Why This Scope

Two ideas are being combined:

### FinSight contribution
- Broad financial-intelligence platform vision
- Structured + unstructured data
- Hybrid retrieval / RAG
- Deterministic analytics
- Predictive / scoring mindset
- ESG as a first-class analytical dimension
- Scenario simulation
- Explainable recommendations

### Aegis contribution
- Concrete banking workflow
- SME financing use case
- Banca d'Italia + Lombardia public-data angle
- Agentic tool routing
- Regional credit conditions
- Sector-performance analysis
- Structured decision output
- Audit trail
- Demo fallback / Magic String

### Principle

**FinSight is the platform story. Aegis is the focused banking intelligence module that proves the platform.**

---

# 3. Product Scope

## P0 — Must work

1. SME financing request input
2. Financial / company data ingestion
3. Public economic data ingestion
4. At least one supporting document (PDF) ingestion
5. Data cleaning / normalization
6. Structured storage (DuckDB)
7. Four decision tools:
   - company financials
   - regional risk
   - sector performance
   - document / policy retrieval
8. LLM orchestration via LangGraph or equivalent
9. Deterministic financial score
10. Deterministic ESG score
11. Evidence-backed explanation
12. Scenario simulation for one financing change
13. Streamlit dashboard
14. Structured JSON contract between backend and UI
15. Demo fallback path

## P1 — Only if P0 is stable

- Simple trend / forecast
- Basic anomaly flag
- More sophisticated document retrieval
- Second scenario
- Better charts / animation

## P2 — Post-hackathon

- Full portfolio module
- Full wealth-management workspace
- Knowledge graph / ontology
- Portfolio optimisation
- Multiple ML models
- Live bank APIs
- Authentication / multi-tenancy
- Production database
- Continuous monitoring / alerts

---

# 4. Golden Rule for the Architecture

## The LLM is NOT the financial calculator.

The system must separate:

### A. Deterministic engine
Calculates:
- ratios
- scores
- trends
- scenario changes
- thresholds

### B. Retrieval engine
Finds:
- company-document evidence
- policy evidence
- source passages
- supporting public-data context

### C. LLM / agent
Handles:
- intent understanding
- tool selection
- orchestration
- synthesis
- human-readable explanation
- structured final response

The LLM should explain trusted calculations, not invent them.

---

# 5. End-to-End Architecture

```text
                              ┌──────────────────────────────┐
                              │        BANK USER             │
                              │ Relationship / Credit Officer│
                              └──────────────┬───────────────┘
                                             │
                                             ▼
                              ┌──────────────────────────────┐
                              │       SME APPLICATION        │
                              │                              │
                              │ Company / sector / region   │
                              │ Loan amount / purpose        │
                              │ Uploaded financial files    │
                              └──────────────┬───────────────┘
                                             │
                                             ▼
                         ┌────────────────────────────────────────┐
                         │             DATA INGESTION             │
                         │ PDF | CSV | Excel | Public datasets  │
                         └──────────────────┬─────────────────────┘
                                            │
                       ┌────────────────────┴────────────────────┐
                       ▼                                         ▼
            ┌────────────────────────┐              ┌────────────────────────┐
            │ STRUCTURED DATA LAYER │              │ DOCUMENT / RAG LAYER   │
            │                        │              │                        │
            │ DuckDB                 │              │ PDF extraction         │
            │ company financials     │              │ chunking               │
            │ regional risk          │              │ embeddings              │
            │ sector performance     │              │ vector / keyword search │
            │ ESG indicators         │              │ policy evidence         │
            └────────────┬───────────┘              └────────────┬───────────┘
                         │                                       │
                         └──────────────────┬────────────────────┘
                                            ▼
                                ┌────────────────────────┐
                                │    LLM ORCHESTRATOR    │
                                │      LangGraph         │
                                │                        │
                                │ Understand request     │
                                │ Select required tools  │
                                │ Manage execution       │
                                └────────────┬───────────┘
                                             │
                      ┌──────────────────────┼──────────────────────┐
                      ▼                      ▼                      ▼
             ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
             │ FINANCIAL TOOL │    │  REGIONAL TOOL │    │   SECTOR TOOL  │
             │                │    │                │    │                │
             │ company ratios │    │ liquidity/risk │    │ growth/outlook │
             └───────┬────────┘    └───────┬────────┘    └───────┬────────┘
                     │                     │                     │
                     └─────────────────────┼─────────────────────┘
                                           ▼
                                  ┌─────────────────┐
                                  │   RAG TOOL      │
                                  │ documents /     │
                                  │ policies / ESG  │
                                  └────────┬────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │   DETERMINISTIC ENGINES │
                              │                         │
                              │ Financial Score        │
                              │ ESG Score              │
                              │ Scenario Calculation   │
                              └────────────┬────────────┘
                                           │
                                           ▼
                               ┌────────────────────────┐
                               │     LLM EXPLAINER      │
                               │                        │
                               │ Evidence + reasoning   │
                               │ Structured output      │
                               └────────────┬───────────┘
                                            │
                                            ▼
                              ┌─────────────────────────┐
                              │       FASTAPI            │
                              │     POST /evaluate      │
                              └────────────┬────────────┘
                                           │ JSON
                                           ▼
                              ┌─────────────────────────┐
                              │       STREAMLIT          │
                              │ Dashboard + AI trace    │
                              └─────────────────────────┘
```

---

# 6. Data Sources

The exact organiser dataset names and available fields determine what can be implemented. The architecture assumes these categories:

## Public structured data

### Banca d'Italia
Use available regional credit / lending / deposits indicators relevant to the challenge.

Potential outputs:
- regional liquidity indicator
- lending / credit conditions
- default / risk indicators if available
- interest-rate indicators if available

### Open Data Lombardia
Use available enterprise / sector / economic indicators.

Potential outputs:
- sector turnover
- active enterprises
- sector growth
- provincial / sector economic indicators

## Applicant data

For the hackathon, use fictional / synthetic SME data if real customer data is unavailable.

Potential fields:

```text
company_name
province
sector
annual_revenue
ebitda
cash
debt
annual_interest
employees
loan_amount
loan_purpose
```

## Document data

At minimum:
- one company financial report or synthetic company report
- one sustainability / ESG document OR policy document

The document layer should provide evidence, not numerical truth where structured data exists.

---

# 7. Data Pipeline

```text
RAW FILES
   ↓
FILE DETECTION
   ↓
VALIDATION
   ↓
EXTRACTION
   ↓
CLEANING
   ↓
NORMALIZATION
   ↓
ENTITY / NAME STANDARDIZATION
   ↓
DUCKDB + DOCUMENT INDEX
   ↓
READY FOR TOOLS
```

## Required cleaning

- Standardize province names (`Milano` vs `Milan`)
- Standardize sector labels
- Normalize dates
- Normalize currency to EUR where appropriate
- Remove duplicates
- Handle missing values explicitly
- Validate numeric ranges
- Preserve raw files separately from processed data

---

# 8. Minimal DuckDB Schema

Use the smallest schema that supports the demo.

## `company_financials`

```text
company_id
company_name
province
sector
revenue
ebitda
cash
short_term_debt
long_term_debt
interest_expense
employees
revenue_growth
```

## `regional_risk`

```text
province
year
liquidity_indicator
avg_interest_rate
loan_default_rate
```

Only include fields that actually exist in the released dataset; do not fabricate unavailable metrics.

## `sector_performance`

```text
province
sector_name
year
aggregate_turnover
active_enterprises
economic_performance_index
```

Again, adapt to the organiser dataset schema.

## `esg_data`

```text
company_id / company_name
sector
environmental_indicator
social_indicator
governance_indicator
carbon_exposure
esg_evidence_source
```

## `documents`

```text
document_id
company_id
source_name
document_type
chunk_id
text_content
metadata
```

---

# 9. Agent Tools

The backend exposes a small, fixed toolset.

## Tool 1 — Company Financials

```python
get_company_financials(company_name)
```

Returns trusted structured financial values and derived ratios.

## Tool 2 — Regional Risk

```python
get_regional_risk(province)
```

Returns the latest relevant regional indicators available in the dataset.

## Tool 3 — Sector Performance

```python
get_sector_performance(province, sector)
```

Returns sector trend / growth indicators.

## Tool 4 — Document Search

```python
search_documents(query, company_name=None)
```

Returns relevant chunks with source metadata.

## Optional Tool 5 — Scenario

```python
simulate_financing_scenario(base_metrics, scenario)
```

This is deterministic code, not an LLM tool.

---

# 10. Agent Behaviour

Example user request:

> "Assess a €750k sustainability-linked equipment loan for EcoTex Milano, a textile manufacturer in Milan."

The agent should infer:

```json
{
  "company": "EcoTex Milano",
  "province": "Milano",
  "sector": "Textile Manufacturing",
  "loan_amount": 750000,
  "loan_purpose": "Sustainability-linked equipment"
}
```

Then call the relevant tools:

```text
Company Financials
        ↓
Regional Risk
        ↓
Sector Performance
        ↓
Document / ESG Evidence
        ↓
Scoring Engine
        ↓
Final Explanation
```

The exact routing can be LLM-driven, but the available tools and outputs must remain constrained.

---

# 11. Financial Scoring Engine

The financial score must be deterministic and explainable.

Example prototype weighting:

```text
Liquidity / cash position        25%
Leverage / debt burden           25%
Revenue growth                   20%
Sector outlook                   15%
Regional credit conditions       15%
```

Output:

```text
Financial Health Score: 0–100
Risk Level: Low / Medium / High
Drivers: list of quantitative drivers
```

### Important

These weights are a **prototype methodology**, not an official bank credit model or regulatory score.

---

# 12. ESG Scoring Engine

Example prototype weighting:

```text
Environmental impact             50%
Project / financing alignment    25%
Transition potential             15%
Evidence quality                 10%
```

Output:

```text
ESG Alignment Score: 0–100
ESG Level: Low / Medium / High
Drivers: evidence-backed factors
```

The UI must label this as a **prototype methodology** and never present it as an official regulatory ESG rating.

---

# 13. Scenario Engine

The scenario engine is deterministic.

### Primary scenario

> "What happens if the bank increases the loan from €750k to €1m?"

Recalculate:

- debt burden
- interest burden
- financial score
- overall risk level
- recommendation threshold

Keep ESG constant unless the financing structure changes the underlying project or ESG assumptions.

### Example

```text
CURRENT                         SCENARIO
€750k                           €1.0M

Financial score  82      →      74
ESG score        91      →      91
Risk             Medium  →      High
Assessment       APPROVE →      REVIEW
```

Numbers shown above are demo placeholders only. The application must calculate its final numbers from the actual seeded data and scoring rules.

---

# 14. Recommendation Engine

Do not let the LLM invent the decision.

Implement an explicit rule layer.

Example:

```text
Financial score >= 75
AND ESG score >= 70
AND no critical risk flag
        ↓
     APPROVE

Financial score 55–74
OR material unresolved evidence
        ↓
      REVIEW

Financial score < 55
OR critical risk flag
        ↓
      DECLINE
```

Thresholds are prototype thresholds and must be clearly labelled as such.

The LLM then explains **why** the deterministic engine produced the result.

---

# 15. Structured API Contract

The frontend and backend must use a fixed contract so all three teammates can work independently.

## Endpoint

```http
POST /evaluate
```

## Request

```json
{
  "query": "Assess a €750k sustainability-linked equipment loan for EcoTex Milano in Milan."
}
```

## Response

```json
{
  "company": "EcoTex Milano",
  "loan_amount": 750000,
  "financial_score": 82,
  "esg_score": 91,
  "risk_level": "Medium",
  "sector_outlook": "Positive",
  "recommendation": "APPROVE",
  "confidence": 0.87,
  "drivers": [
    "Positive revenue trajectory",
    "Favourable sector conditions",
    "Strong project ESG alignment"
  ],
  "evidence": [
    {
      "source": "Banca d'Italia",
      "claim": "Regional credit conditions support the assessment."
    },
    {
      "source": "Open Data Lombardia",
      "claim": "Sector indicators show a positive trend."
    }
  ],
  "audit_trail": [
    "Company financials queried",
    "Regional risk queried",
    "Sector performance queried",
    "ESG evidence retrieved"
  ],
  "scenario": {
    "loan_amount": 1000000,
    "financial_score": 74,
    "esg_score": 91,
    "risk_level": "High",
    "recommendation": "REVIEW"
  },
  "summary": "The application is financially supportable under the base case, with strong ESG alignment. Increasing financing to €1M materially increases financial risk."
}
```

---

# 16. Streamlit UX

The UI is a major part of the pitch.

## Main screen

### Header

```text
FinSight AI
Financial Intelligence & Decision Engine
```

### Application card

Show:
- company
- sector
- province
- requested financing
- financing purpose

### KPI area

```text
Financial Health      ESG Alignment       Risk
     82/100              91/100          Medium
```

### AI decision trace

Visually show:

```text
User request
     ↓
Company Financials ✓
     ↓
Regional Risk ✓
     ↓
Sector Performance ✓
     ↓
Document Evidence ✓
     ↓
Scoring Engine ✓
     ↓
Recommendation
```

### Why?

Show the 3–5 strongest drivers.

### Evidence

Show source names and short evidence excerpts.

### What-if section

Interactive slider / select:

```text
Loan amount
€500k ────────●────── €1.5M
```

Then update:
- financial score
- risk
- recommendation

### Disclaimer

Prototype decision support only. Not financial advice, not an official credit rating, and not a substitute for human underwriting / compliance review.

---

# 17. Team Ownership

## Teammate A — Data / Analytics

### Owns
- raw dataset collection
- schema inspection
- cleaning
- normalization
- DuckDB
- deterministic scoring calculations
- scenario calculations

### Deliverables

```text
data/raw/
data/processed/
data/duckdb/

scripts/ingest.py
analytics/scoring.py
analytics/scenario.py
```

### Handoff to B

Must provide:
- database file
- table names
- column names
- example queries
- Python functions
- sample outputs

---

## Teammate B — AI / Backend

### Owns
- LangGraph orchestration
- tool definitions
- LLM integration
- RAG search
- FastAPI
- Pydantic schemas
- recommendation orchestration
- fallback / error handling

### Deliverables

```text
backend/main.py
backend/tools.py
backend/agent.py
backend/schemas.py
backend/rag.py
```

### Handoff to C

Must provide:

```text
POST /evaluate
```

with the exact response contract from Section 15.

---

## Teammate C — Product / UI / Pitch

### Owns
- Streamlit dashboard
- interaction design
- loading states
- score cards
- AI trace
- scenario interaction
- source/evidence presentation
- demo experience
- pitch narrative

### Deliverables

```text
app.py
ui/
assets/
```

C must begin with mock JSON and must **not wait for B**.

---

# 18. Four-Hour Execution Plan

## 00:00–00:20 — Lock the contract

### Everyone
- agree on company
- agree on exact demo query
- agree on schema
- agree on response JSON
- create shared repo
- create branches

### Decision

```text
Company: EcoTex Milano
Province: Milano
Sector: Textile Manufacturing
Loan: €750k
Purpose: sustainability-linked equipment
```

---

## 00:20–01:20 — Parallel build

### A
```text
Inspect datasets
   ↓
Clean
   ↓
Normalize
   ↓
DuckDB
   ↓
Financial/risk/sector functions
```

### B
```text
FastAPI
   ↓
Pydantic schemas
   ↓
4 tools
   ↓
LangGraph routing
   ↓
LLM response
```

Use mock data until A is ready.

### C
```text
Streamlit shell
   ↓
Mock API response
   ↓
Dashboard
   ↓
Scenario UI
   ↓
AI trace
```

---

## 01:20–02:10 — Connect

A hands database + functions to B.

B connects tools to real data.

C points UI to:

```text
http://localhost:8000/evaluate
```

Run the first complete end-to-end query.

**Definition of success:** one query goes from UI → API → agent → tools → scoring → JSON → UI.

---

## 02:10–03:00 — Reliability + polish

### A
- edge cases
- missing province
- missing sector
- missing company data

### B
- timeout handling
- LLM failure handling
- structured JSON validation
- deterministic recommendation
- Magic String fallback

### C
- layout polish
- animations only where they help
- source cards
- score visualization
- scenario interaction

---

## 03:00–04:00 — Demo defense

### Freeze feature scope.

No new modules.

### Required

```text
✓ Happy path works
✓ Magic String works
✓ Local data works
✓ UI does not crash on API failure
✓ Backup recording exists
✓ Pitch is rehearsed
✓ Architecture diagram is ready
```

---

# 19. Demo Script

## 0:00–0:30 — Problem

Financial institutions have data across reports, structured systems, public economic datasets, and ESG information. The problem is not a lack of data; it is turning the data into a decision quickly and explaining the decision.

## 0:30–1:00 — Product

> "FinSight is an AI financial intelligence layer for banks. For this prototype, we focus on one decision: evaluating an SME financing proposal with both financial and sustainability context."

## 1:00–1:45 — Architecture

Explain:

```text
Structured data → deterministic analytics
Documents → RAG / evidence
LLM → orchestration + explanation
Scenario engine → what-if impact
```

## 1:45–3:30 — Live demo

Enter:

> **Assess a €750k sustainability-linked equipment loan for EcoTex Milano, a textile manufacturer in Milan.**

Show:
- financial score
- ESG score
- regional risk
- sector outlook
- evidence
- audit trail

Then ask:

> **What happens if financing increases to €1M?**

Show score / risk / recommendation change.

## 3:30–4:30 — Why it matters

Explain that the system connects fragmented information to a transparent decision-support workflow rather than using an LLM as a black-box calculator.

## 4:30–5:00 — Scale

> "Today's prototype proves the credit-intelligence layer. The same architecture can expand into portfolio intelligence, monitoring, forecasting, ESG optimisation and broader wealth-management workflows."

---

# 20. Demo Fallback Protocol

## Magic String

Use one agreed exact query:

```text
Assess a €750k sustainability-linked equipment loan for EcoTex Milano, a textile manufacturer in Milan.
```

If this exact request is received, the backend may return a precomputed demo payload.

Purpose:
- protect against Wi-Fi failure
- protect against LLM rate limits
- protect against temporary upstream outages
- guarantee the visual punchline

## Backup video

Record the happy path locally before presentation.

The backup video must show:

```text
Input
 → agent trace
 → data tools
 → scores
 → scenario
 → final recommendation
```

Do not debug live on stage.

---

# 21. Error Handling

Backend must never return an unhandled exception to the UI.

Example:

```json
{
  "status": "error",
  "message": "The live reasoning service is temporarily unavailable.",
  "fallback_available": true
}
```

UI should show a useful state instead of a blank screen.

---

# 22. Repository Structure

```text
finsight-ai/
│
├── app.py                         # Streamlit entry point
├── README.md
├── PROJECT.md                     # This document
├── requirements.txt
├── .env.example
│
├── backend/
│   ├── main.py                    # FastAPI
│   ├── agent.py                   # LangGraph / orchestration
│   ├── tools.py                   # Tool definitions
│   ├── schemas.py                 # Pydantic contracts
│   └── rag.py                     # Document retrieval
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── finsight.duckdb
│
├── ingestion/
│   ├── loaders.py
│   ├── cleaner.py
│   └── normalizer.py
│
├── analytics/
│   ├── financial.py
│   ├── scoring.py
│   ├── esg.py
│   └── scenario.py
│
├── rag/
│   ├── embeddings.py
│   ├── retrieval.py
│   └── documents.py
│
├── ui/
│   ├── components.py
│   └── styles.py
│
├── assets/
│   ├── demo_video.mp4
│   └── architecture.png
│
└── scripts/
    ├── ingest_data.py
    └── seed_demo.py
```

---

# 23. Collaboration Rules

## Shared contract first

No teammate should change the response schema without announcing it.

## One branch per owner

```text
main
├── teammate-a-data
├── teammate-b-ai
└── teammate-c-ui
```

## Integration rule

Every teammate must provide:
- what changed
- which files changed
- how to run it
- example input
- example output
- anything the next teammate needs to know

## Communication template

When handing off:

```text
DONE:
- What I finished

FILES:
- path/to/file.py

CONTRACT:
- function / endpoint / schema

TEST:
- command used

EXAMPLE:
- input
- output

BLOCKERS:
- none / details
```

## No hidden dependencies

Never rely on:
- a teammate's local-only file path
- uncommitted code
- undocumented environment variables
- manually edited database state

---

# 24. Acceptance Criteria

The project is "done" for the hackathon when all are true:

### Data
- [ ] At least one structured public dataset is loaded.
- [ ] Applicant data is queryable.
- [ ] At least one document is searchable.
- [ ] Province / sector normalization works.

### AI
- [ ] Agent receives a natural-language financing request.
- [ ] Agent selects appropriate tools.
- [ ] RAG returns source-backed evidence.
- [ ] LLM does not calculate financial metrics itself.
- [ ] Output validates against Pydantic schema.

### Analytics
- [ ] Financial score is deterministic.
- [ ] ESG score is deterministic.
- [ ] Risk level is rule-based.
- [ ] Scenario engine recalculates loan impact.

### UI
- [ ] Dashboard renders without manual editing.
- [ ] Scores are obvious.
- [ ] AI/tool trace is visible.
- [ ] Evidence is visible.
- [ ] Scenario can be demonstrated.
- [ ] Error state does not break the page.

### Demo
- [ ] Exact happy-path query works.
- [ ] Magic String fallback works.
- [ ] Backup recording exists.
- [ ] Full demo runs on the presentation machine.

---

# 25. Out-of-Scope Rules

During the four-hour build, say **NO** to:

- full banking core integration
- production credit underwriting
- customer authentication
- multi-tenant architecture
- portfolio optimisation
- knowledge graph implementation
- complex forecasting pipelines
- multiple ML models
- live bank APIs
- full regulatory certification
- broad chatbot functionality
- more than one polished scenario

The product can promise these later. The demo does not need them today.

---

# 26. Responsible AI / Compliance Positioning

Use this language:

> **FinSight is an AI-assisted financial decision-support prototype. It provides evidence-backed analytics and scenario analysis for human review. It does not provide regulated financial advice, represent an official credit rating, or replace a bank's formal underwriting and compliance process.**

The system should distinguish:

```text
FACT
→ retrieved / structured source

CALCULATION
→ deterministic engine

PREDICTION
→ model estimate, if implemented

RECOMMENDATION
→ prototype rule / decision-support output
```

---

# 27. Success Metrics for the Hackathon

The technical goal is not maximum feature count.

Measure success by:

### End-to-end reliability
One complete financing request works repeatedly.

### Explainability
Every major score has visible drivers.

### Grounding
Document claims can be traced to sources.

### Determinism
Repeated inputs produce consistent scores where the same data and rules are used.

### Demo quality
The judges can understand the system within seconds.

### Scalability story
The architecture clearly supports future FinSight modules.

---

# 28. Long-Term Product Expansion

After the hackathon, the same platform can expand:

```text
                 FINSIGHT AI
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
   CREDIT/SME      WEALTH         ESG / SUSTAINABILITY
   INTELLIGENCE    INTELLIGENCE       INTELLIGENCE
       │              │              │
       └──────────────┼──────────────┘
                      ▼
                SHARED AI LAYER
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
      RAG        ANALYTICS       SCENARIOS
                      │
                      ▼
             DECISION SUPPORT
```

Potential future modules:
- portfolio health
- advisor co-pilot
- anomaly monitoring
- forecasting
- ESG optimisation
- client reporting
- automated alerts
- bank / accounting integrations
- embedded APIs / SDKs

---

# 29. Final Build Order

```text
1. LOCK USER + DEMO CASE
        ↓
2. LOCK DATA / API CONTRACTS
        ↓
3. BUILD DUCKDB + CLEAN DATA
        ↓
4. BUILD DETERMINISTIC FINANCIAL + ESG SCORING
        ↓
5. BUILD BACKEND TOOLS
        ↓
6. BUILD RAG
        ↓
7. BUILD LANGGRAPH ORCHESTRATION
        ↓
8. CONNECT FASTAPI
        ↓
9. CONNECT STREAMLIT
        ↓
10. ADD SCENARIO ENGINE
        ↓
11. ADD AUDIT / EVIDENCE TRACE
        ↓
12. ADD MAGIC STRING FALLBACK
        ↓
13. TEST END-TO-END
        ↓
14. FREEZE FEATURES
        ↓
15. REHEARSE DEMO
```

---

# 30. Final Team Principle

> **Build one thing end-to-end, make it beautiful, make every number explainable, and make the architecture extensible.**

Do not try to prove that FinSight can do everything.

Prove that it can take a real banking question, combine structured financial data with evidence from documents and economic context, calculate a transparent result, simulate an alternative, and explain the decision to a human.

That is the product.
