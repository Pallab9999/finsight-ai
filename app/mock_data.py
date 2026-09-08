"""
FinSight AI - Deterministic Mock Data & Scenario Calculation Engine
===================================================================
Single Source of Truth for frontend testing and hackathon demo fallback.
Conforms strictly to Section 15 and Section 20 of PROJECT_2.md.

HANDOFF NOTE FOR TEAMMATE B (Backend / AI Engine):
The FastAPI endpoint `POST /evaluate` must return a JSON payload with
identical key names and types as `get_base_demo_payload()`.
"""

from typing import Dict, Any, List


def get_base_demo_payload() -> Dict[str, Any]:
    """
    Standard precomputed demo payload for the Magic Query:
    'Assess a €750k sustainability-linked equipment loan for EcoTex Milano, a textile manufacturer in Milan.'
    Guarantees 0% crash risk and sub-millisecond response during live hackathon demos.
    """
    return {
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


def calculate_scenario(base_payload: Dict[str, Any], requested_amount: int) -> Dict[str, Any]:
    """
    Deterministic What-If Scenario Calculation Engine.
    Conforms to Golden Rule: Formulaic mathematics, NO LLM hallucination.
    
    Formula model:
    - Base loan: €750,000 -> Score: 82, Risk: Medium, Recommendation: APPROVE
    - Sensitivity: Each €50k increase increases debt service burden and lowers financial score.
    - At €1,000,000 -> Score: 74, Risk: High, Recommendation: REVIEW
    - At > €1,250,000 -> Score < 65, Risk: High, Recommendation: DECLINE
    """
    base_amount = 750000
    delta = requested_amount - base_amount
    
    # Financial score degradation: approx -1.6 points per €50,000 additional borrowing
    delta_chunks = delta / 50000
    calculated_financial_score = int(round(82 - (delta_chunks * 1.6)))
    calculated_financial_score = max(35, min(95, calculated_financial_score))
    
    # DSCR degradation model
    base_dscr = 1.68
    calculated_dscr = round(max(0.85, base_dscr - (delta / 1000000) * 1.60), 2)
    
    # Risk Level & Recommendation Thresholds (Section 14 & 15)
    if calculated_financial_score >= 80:
        risk_level = "Low" if calculated_financial_score >= 88 else "Medium"
        recommendation = "APPROVE"
        confidence = 0.88
    elif calculated_financial_score >= 70:
        risk_level = "High"
        recommendation = "REVIEW"
        confidence = 0.81
    else:
        risk_level = "High"
        recommendation = "DECLINE"
        confidence = 0.85
        
    summary_text = (
        f"At €{requested_amount:,.0f}, projected Debt Service Coverage Ratio is {calculated_dscr:.2f}x. "
        f"Financial Health score shifts to {calculated_financial_score}/100 ({'+' if calculated_financial_score >= 82 else ''}{calculated_financial_score - 82} pts). "
        f"Decision status is {recommendation}."
    )
    
    return {
        "loan_amount": requested_amount,
        "financial_score": calculated_financial_score,
        "esg_score": base_payload.get("esg_score", 91),
        "risk_level": risk_level,
        "recommendation": recommendation,
        "confidence": confidence,
        "dscr": calculated_dscr,
        "summary": summary_text
    }
