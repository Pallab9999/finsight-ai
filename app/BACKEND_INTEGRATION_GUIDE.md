# FinSight AI - Teammate B Backend Handoff Guide

## Overview
This document specifies the communication contract between the **Streamlit UI** (Teammate C) and the **FastAPI Backend / AI Engine** (Teammate B).

The frontend is already built, styled, and verified. It includes an antifragile auto-failover protocol: if the backend is offline or returns an unhandled error, the UI falls back to the deterministic mock payload from Section 15 of `PROJECT_2.md`.

---

## 1. Fast Track: Running the UI

```bash
# Launch Streamlit
py -3.11 -m streamlit run app/main.py --server.port 8501
```

By default, the UI runs in **"Deterministic Fallback (Demo Safe)"** mode. You can switch to **"Live API (FastAPI)"** in the left sidebar once your server is running.

---

## 2. API Endpoint Specification

- **Method**: `POST`
- **Path**: `/evaluate`
- **Default Port**: `http://localhost:8000/evaluate` (configurable in the Streamlit sidebar)

### Request Payload (`POST /evaluate`)

```json
{
  "query": "Assess a €750k sustainability-linked equipment loan for EcoTex Milano, a textile manufacturer in Milan.",
  "loan_amount": 750000
}
```

### Response Payload Schema (`200 OK`)

Your backend must return a JSON payload with the following fields:

```json
{
  "company": "EcoTex Milano",
  "sector": "Sustainable Technical Textiles",
  "province": "Milan (Lombardia)",
  "loan_amount": 750000,
  "loan_purpose": "Energy-efficient dyeing equipment & closed-loop water recycling plant",
  "financial_score": 82,
  "esg_score": 91,
  "risk_level": "Medium",
  "sector_outlook": "Positive",
  "recommendation": "APPROVE",
  "confidence": 0.87,
  "drivers": [
    "Positive revenue trajectory (+14.2% YoY to €14.2M)",
    "Robust liquidity buffer (Cash/Short-Term Debt at 1.42x)",
    "Favourable sector conditions (Lombardia industrial textile output +4.1% YoY)",
    "Regional credit benchmark stability (Banca d'Italia NPL rate in Milan at 1.82%)",
    "Exceptional ESG alignment (Projected 42% water consumption reduction)"
  ],
  "evidence": [
    {
      "source": "Banca d'Italia - Statistical Database",
      "category": "FACT",
      "claim": "Provincial commercial credit default rate in Milan stands at 1.82%, well below the national SME average of 2.95%."
    },
    {
      "source": "Open Data Lombardia - Regional Enterprise Census",
      "category": "FACT",
      "claim": "Textile and technical apparel sector in Lombardia registered +4.1% YoY turnover growth with expanding export margins."
    },
    {
      "source": "EcoTex Milano - 2024 Audited Financials & ESG Disclosure",
      "category": "FACT",
      "claim": "2024 EBITDA margin recorded at 18.5% (€2.63M) with Net Debt / EBITDA ratio of 1.35x prior to the requested financing."
    },
    {
      "source": "FinSight Deterministic Scoring Engine",
      "category": "CALCULATION",
      "claim": "At €750,000 principal, projected DSCR (Debt Service Coverage Ratio) remains resilient at 1.68x against 5.25% cost of debt."
    },
    {
      "source": "FinSight Synthesis Layer",
      "category": "REASONING",
      "claim": "Strong project additionality: equipment qualifies for regional decarbonization capital grants, de-risking downside exposure."
    }
  ],
  "audit_trail": [
    "Applicant request parsed and validated against schema",
    "Queried structured financials from DuckDB (`companies`, `financial_statements`)",
    "Queried regional credit risk benchmark from Banca d'Italia dataset (`bdi_provincial_credit`)",
    "Queried sector growth and turnover indicators from Open Data Lombardia (`lombardia_sectors`)",
    "Retrieved 3 relevant grounding chunks from EcoTex 2024 ESG Audit report (Cosine similarity > 0.84)",
    "Executed deterministic multi-factor scoring engine (Liquidity 25%, Leverage 25%, Growth 20%, Sector 15%, Region 15%)",
    "Generated structured synthesis and rule-based recommendation"
  ],
  "scenario": {
    "loan_amount": 1000000,
    "financial_score": 74,
    "esg_score": 91,
    "risk_level": "High",
    "recommendation": "REVIEW",
    "dscr": 1.28,
    "leverage_ratio": 1.95,
    "summary": "Increasing financing to €1.0M compresses Debt Service Coverage from 1.68x to 1.28x. Financial score drops by 8 points into High Risk tier, triggering senior underwriter review."
  },
  "summary": "The application is financially sound under the €750,000 base case with robust debt service coverage (1.68x) and exceptional ESG alignment. Increasing facility to €1,000,000 materially elevates leverage, shifting recommendation from APPROVE to REVIEW."
}
```

---

## 3. The Golden Rule of Integration

> **The LLM is NOT the financial calculator.**
> `financial_score`, `esg_score`, `dscr`, `risk_level`, and `recommendation` must be computed by your deterministic Python formulas / DuckDB views.
> The LLM's sole responsibility is to synthesize the drivers, audit trail, and natural language summary based on those numbers.

---

## 4. Frontend Integration Layer (`app/api_client.py`)

The frontend calls your API through `app/api_client.py`.
- If your backend is running: the UI displays `🟢 LIVE FASTAPI ENGINE: Successfully evaluated via FastAPI backend`.
- If your backend fails or times out (4.0s timeout): the UI smoothly falls back without crashing and displays `🟡 DEMO SAFE MODE`.
