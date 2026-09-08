"""LLM orchestration: tool routing, scoring, explanation synthesis."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from analytics.esg import score_esg
from analytics.financial import compute_ratios
from analytics.scenario import simulate_scenario
from analytics.scoring import (
    classify_risk,
    classify_sector_outlook,
    compute_confidence,
    compute_financial_score,
    recommend,
)
from backend.config import settings
from backend.fallback import get_fallback_response, is_magic_query
from backend.llm import generate_summary
from backend.schemas import EvaluateResponse, EvidenceItem, ScenarioResult
from backend.tools import (
    get_company_financials,
    get_regional_risk,
    get_sector_performance,
    search_documents,
)
from ingestion.cleaner import standardize_province, standardize_sector
from ingestion.loaders import get_connection, seed_database, ensure_sme_profiles

logger = logging.getLogger(__name__)

AUDIT_TRAIL: list[str] = []


def _ensure_database() -> None:
    bankbench = settings.bankbench_sqlite_path or None
    from pathlib import Path

    if not settings.duckdb_path.exists():
        seed_database(settings.duckdb_path, Path(bankbench) if bankbench else None)
    else:
        ensure_sme_profiles(settings.duckdb_path)


def parse_query(query: str) -> dict[str, Any]:
    """Extract structured fields from natural language financing request."""
    q = query.strip()
    q_lower = q.lower()

    company = "EcoTex Milano"
    if "meccanica" in q_lower or "varese" in q_lower:
        company = "Meccanica Precisione Varese"
    elif "agrobio" in q_lower or "brianza" in q_lower:
        company = "AgroBio Brianza"
    elif "ecotex" in q_lower:
        company = "EcoTex Milano"
    elif match := re.search(r"for\s+([A-Za-z0-9\s&\-\.]+?)(?:,|\s+a\s|\s+in\s|$)", q, re.I):
        company = match.group(1).strip().rstrip(",")

    province = "Milano"
    if "milan" in q_lower or "milano" in q_lower:
        province = "Milano"
    elif "varese" in q_lower:
        province = "Varese"
    elif "brianza" in q_lower or "monza" in q_lower:
        province = "Monza e Brianza"
    elif match := re.search(r"\bin\s+([A-Za-z\s]+?)(?:\.|$|,)", q, re.I):
        province = standardize_province(match.group(1).strip())

    sector = "Textile Manufacturing"
    if "textile" in q_lower:
        sector = "Textile Manufacturing"
    elif "cnc" in q_lower or "aerospace" in q_lower or "machin" in q_lower:
        sector = "Precision Machining"
    elif "agri" in q_lower or "pack" in q_lower or "organic" in q_lower:
        sector = "Agri-Food"
    elif "manufactur" in q_lower:
        sector = "Manufacturing"

    loan_amount = 750_000
    if match := re.search(r"€?\s*([\d.,]+)\s*[kK]", q):
        loan_amount = int(float(match.group(1).replace(",", ".")) * 1000)
    elif match := re.search(r"€?\s*([\d.,]+)", q):
        val = float(match.group(1).replace(",", "").replace(".", ""))
        if val < 10000:
            val *= 1000
        loan_amount = int(val)

    purpose = "equipment financing"
    if "sustainability" in q_lower or "green" in q_lower:
        purpose = "sustainability-linked equipment"
    elif "working capital" in q_lower:
        purpose = "working capital"

    return {
        "company": company.strip(),
        "province": standardize_province(province),
        "sector": standardize_sector(sector),
        "loan_amount": loan_amount,
        "loan_purpose": purpose,
    }


def _build_evidence(
    regional: dict[str, Any],
    sector: dict[str, Any],
    doc_results: list[dict[str, Any]],
) -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []

    if "error" not in regional:
        evidence.append(
            EvidenceItem(
                source="Banca d'Italia / Regional Data",
                category="FACT",
                claim=(
                    f"Regional liquidity indicator at {regional.get('liquidity_indicator', 0):.0%} "
                    f"with default rate {regional.get('loan_default_rate', 0)*100:.1f}% in {regional.get('province', 'region')}."
                ),
            )
        )

    if "error" not in sector:
        evidence.append(
            EvidenceItem(
                source="Open Data Lombardia",
                category="FACT",
                claim=(
                    f"Sector '{sector.get('sector_name')}' performance index "
                    f"{sector.get('economic_performance_index', 1.0):.2f} "
                    f"with {sector.get('active_enterprises', 0):,} active enterprises."
                ),
            )
        )

    for doc in doc_results[:2]:
        evidence.append(
            EvidenceItem(
                source=doc.get("source", "Document"),
                category="FACT",
                claim=doc.get("text", "")[:200],
            )
        )

    return evidence


def _generate_summary(
    parsed: dict[str, Any],
    financial_score: int,
    esg_score: int,
    risk_level: str,
    recommendation: str,
    drivers: list[str],
    scenario: dict[str, Any],
) -> str:
    prompt = f"""You are a bank credit analyst assistant. Write a 2-3 sentence executive summary.

Company: {parsed['company']}
Loan: €{parsed['loan_amount']:,} for {parsed['loan_purpose']}
Financial Score: {financial_score}/100
ESG Score: {esg_score}/100
Risk: {risk_level}
Recommendation: {recommendation}
Key drivers: {'; '.join(drivers[:3])}
Scenario (€{scenario['loan_amount']:,}): score {scenario['financial_score']}, {scenario['recommendation']}

Rules: Be direct. Do not invent numbers. Label as decision-support, not advice."""

    text, provider = generate_summary(prompt)
    if text:
        AUDIT_TRAIL.append(f"Executive summary synthesised via {provider}")
        return text

    AUDIT_TRAIL.append("Executive summary generated from deterministic template")
    return (
        f"{parsed['company']} presents a financial health score of {financial_score}/100 and "
        f"ESG alignment of {esg_score}/100 under the base €{parsed['loan_amount']:,} scenario, "
        f"yielding a {recommendation} recommendation with {risk_level.lower()} risk. "
        f"Increasing financing to €{scenario['loan_amount']:,} reduces the financial score to "
        f"{scenario['financial_score']} and shifts the recommendation to {scenario['recommendation']}."
    )


COMPANY_BY_ID = {
    "ecotex": "EcoTex Milano",
    "meccanica": "Meccanica Precisione Varese",
    "agrobio": "AgroBio Brianza",
}


def evaluate_request(
    query: str,
    scenario_loan_amount: int | None = None,
    loan_amount_override: int | None = None,
    company_id: str | None = None,
) -> EvaluateResponse:
    """Full evaluation pipeline."""
    global AUDIT_TRAIL
    AUDIT_TRAIL = []

    _ensure_database()
    parsed = parse_query(query)
    if company_id and company_id in COMPANY_BY_ID:
        parsed["company"] = COMPANY_BY_ID[company_id]
    company = parsed["company"]
    loan_amount = loan_amount_override or parsed["loan_amount"]
    parsed["loan_amount"] = loan_amount
    scenario_amount = scenario_loan_amount or 1_000_000

    AUDIT_TRAIL.append("Query parsed")
    financials = get_company_financials(company)
    AUDIT_TRAIL.append("Company financials queried")
    if "error" in financials:
        if is_magic_query(query):
            return get_fallback_response()
        raise ValueError(financials["error"])

    province = financials.get("province") or parsed["province"]
    sector = financials.get("sector") or parsed["sector"]

    regional = get_regional_risk(province)
    AUDIT_TRAIL.append("Regional risk queried")
    sector_data = get_sector_performance(province, sector)
    AUDIT_TRAIL.append("Sector performance queried")
    doc_results = search_documents(
        f"{parsed['loan_purpose']} ESG sustainability {sector}",
        company_name=company,
    )
    AUDIT_TRAIL.append("ESG evidence retrieved")

    esg_row = _load_esg(company)
    esg_result = score_esg(esg_row, parsed["loan_purpose"])
    ratios = compute_ratios(financials)
    revenue = float(financials.get("revenue", 0) or 0)

    fin_result = compute_financial_score(
        ratios,
        sector_data if "error" not in sector_data else {"economic_performance_index": 1.0},
        regional if "error" not in regional else {"liquidity_indicator": 0.75, "loan_default_rate": 0.02},
        loan_amount,
        revenue,
    )
    AUDIT_TRAIL.append("Deterministic scoring engine executed")

    risk_level = classify_risk(fin_result["financial_score"], esg_result["esg_score"], ratios["leverage_ratio"])
    recommendation = recommend(fin_result["financial_score"], esg_result["esg_score"], risk_level)
    sector_outlook = classify_sector_outlook(
        float(sector_data.get("economic_performance_index", 1.0) if "error" not in sector_data else 1.0)
    )

    sim = simulate_scenario(
        financials,
        esg_row,
        sector_data if "error" not in sector_data else {"economic_performance_index": 1.0},
        regional if "error" not in regional else {"liquidity_indicator": 0.75, "loan_default_rate": 0.02},
        loan_amount,
        scenario_amount,
        parsed["loan_purpose"],
    )
    AUDIT_TRAIL.append("Scenario simulation completed")

    drivers = list(dict.fromkeys(fin_result["drivers"] + esg_result["drivers"]))[:5]
    evidence = _build_evidence(regional, sector_data, doc_results)
    confidence = compute_confidence(fin_result["financial_score"], esg_result["esg_score"], len(evidence))

    scenario_payload = {
        **sim["scenario"],
        "dscr": round(float(ratios.get("interest_coverage", 1.5)) - max(0, (scenario_amount - loan_amount) / 500_000) * 0.15, 2),
        "summary": (
            f"At €{scenario_amount:,}, financial score is {sim['scenario']['financial_score']}/100 "
            f"with recommendation {sim['scenario']['recommendation']}."
        ),
    }
    scenario = ScenarioResult(**scenario_payload)
    summary = _generate_summary(
        parsed,
        fin_result["financial_score"],
        esg_result["esg_score"],
        risk_level,
        recommendation,
        drivers,
        sim["scenario"],
    )

    return EvaluateResponse(
        company=financials.get("company_name", company),
        loan_amount=loan_amount,
        financial_score=fin_result["financial_score"],
        esg_score=esg_result["esg_score"],
        risk_level=risk_level,
        sector_outlook=sector_outlook,
        recommendation=recommendation,
        confidence=confidence,
        drivers=drivers,
        evidence=evidence,
        audit_trail=AUDIT_TRAIL.copy(),
        scenario=scenario,
        summary=summary,
    )


def _load_esg(company_name: str) -> dict[str, Any]:
    conn = get_connection(settings.duckdb_path)
    try:
        row = conn.execute(
            """
            SELECT company_id, company_name, sector, environmental_indicator,
                   social_indicator, governance_indicator, carbon_exposure,
                   evidence_quality, esg_evidence_source
            FROM esg_data WHERE company_name ILIKE ? LIMIT 1
            """,
            [f"%{company_name}%"],
        ).fetchone()
        if not row:
            return {
                "environmental_indicator": 0.5,
                "social_indicator": 0.5,
                "governance_indicator": 0.5,
                "carbon_exposure": 0.5,
                "evidence_quality": 0.5,
            }
        cols = [
            "company_id", "company_name", "sector", "environmental_indicator",
            "social_indicator", "governance_indicator", "carbon_exposure",
            "evidence_quality", "esg_evidence_source",
        ]
        return dict(zip(cols, row, strict=False))
    finally:
        conn.close()
