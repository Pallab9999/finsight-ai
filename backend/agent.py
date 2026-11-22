"""LLM orchestration: tool routing, scoring, explanation synthesis."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from analytics.amounts import parse_amount
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

DEFAULT_LOAN_AMOUNT = 750_000
DEFAULT_SCENARIO_AMOUNT = 1_000_000
# Interest rate assumed on extra (or removed) financing in the what-if scenario.
SCENARIO_INTEREST_RATE = 0.045

NEUTRAL_SECTOR = {"economic_performance_index": 1.0}
NEUTRAL_REGION = {"liquidity_indicator": 0.75, "loan_default_rate": 0.02}
NEUTRAL_ESG = {
    "environmental_indicator": 0.5,
    "social_indicator": 0.5,
    "governance_indicator": 0.5,
    "carbon_exposure": 0.5,
    "evidence_quality": 0.5,
}


class CompanyNotFoundError(LookupError):
    """The request names no company we hold financials for."""


def default_scenario_amount(loan_amount: int) -> int:
    """€1M stress case, or +33% (rounded to €50k) when the loan is already €1M or more."""
    if loan_amount < DEFAULT_SCENARIO_AMOUNT:
        return DEFAULT_SCENARIO_AMOUNT
    return int(round(loan_amount * 4 / 3 / 50_000) * 50_000)


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

    # None when no company can be identified: callers must not silently
    # assess a different company than the one asked about.
    company: str | None = None
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

    loan_amount = parse_amount(q) or DEFAULT_LOAN_AMOUNT

    purpose = "equipment financing"
    if "sustainability" in q_lower or "green" in q_lower:
        purpose = "sustainability-linked equipment"
    elif "working capital" in q_lower:
        purpose = "working capital"

    return {
        "company": company.strip() if company else None,
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
    audit: list[str],
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
        audit.append(f"Executive summary synthesised via {provider}")
        return text

    audit.append("Executive summary generated from deterministic template")
    sc_score = scenario["financial_score"]
    direction = "Increasing" if scenario["loan_amount"] > parsed["loan_amount"] else "Reducing"
    if sc_score < financial_score:
        effect = f"lowers the financial score to {sc_score}"
    elif sc_score > financial_score:
        effect = f"raises the financial score to {sc_score}"
    else:
        effect = f"leaves the financial score at {sc_score}"
    return (
        f"{parsed['company']} presents a financial health score of {financial_score}/100 and "
        f"ESG alignment of {esg_score}/100 under the base €{parsed['loan_amount']:,} scenario, "
        f"yielding a {recommendation} recommendation with {risk_level.lower()} risk. "
        f"{direction} financing to €{scenario['loan_amount']:,} {effect} "
        f"with a {scenario['recommendation']} recommendation."
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
    """Full evaluation pipeline.

    The audit trail is built per call. It used to be a module-level list that
    concurrent requests shared (FastAPI runs sync endpoints in a thread pool),
    so one request could return another request's trail.
    """
    audit: list[str] = []

    _ensure_database()
    parsed = parse_query(query)
    if company_id:
        if company_id not in COMPANY_BY_ID:
            raise CompanyNotFoundError(f"Unknown company_id: {company_id}")
        parsed["company"] = COMPANY_BY_ID[company_id]
    company = parsed["company"]
    if not company:
        if is_magic_query(query):
            return get_fallback_response()
        raise CompanyNotFoundError(
            "Could not identify the company in the request. Name it, e.g. "
            "'Assess a €500k loan for Meccanica Precisione Varese'."
        )
    loan_amount = loan_amount_override or parsed["loan_amount"]
    parsed["loan_amount"] = loan_amount
    scenario_amount = scenario_loan_amount or default_scenario_amount(loan_amount)

    audit.append("Query parsed")
    financials = get_company_financials(company)
    audit.append("Company financials queried")
    if "error" in financials:
        if is_magic_query(query):
            return get_fallback_response()
        raise CompanyNotFoundError(financials["error"])
    company = financials.get("company_name", company)
    parsed["company"] = company

    province = financials.get("province") or parsed["province"]
    sector = financials.get("sector") or parsed["sector"]

    regional = get_regional_risk(province)
    if "error" in regional:
        audit.append(f"Regional risk unavailable for {province}: neutral assumptions used")
        regional_for_scoring = NEUTRAL_REGION
    else:
        audit.append("Regional risk queried")
        regional_for_scoring = regional

    sector_data = get_sector_performance(province, sector)
    if "error" in sector_data:
        audit.append(f"Sector data unavailable for {sector} in {province}: neutral index used")
        sector_for_scoring = NEUTRAL_SECTOR
    else:
        matched = str(sector_data.get("sector_name") or "")
        if sector.lower() not in matched.lower():
            audit.append(f"No sector data for {sector} in {province}: used '{matched}' as proxy")
        else:
            audit.append("Sector performance queried")
        sector_for_scoring = sector_data

    doc_results = search_documents(
        f"{parsed['loan_purpose']} ESG sustainability {sector}",
        company_name=company,
    )
    audit.append("ESG evidence retrieved" if doc_results else "No ESG documents found for company")

    esg_row = _load_esg(company)
    if esg_row is None:
        audit.append("No ESG indicators on file: neutral 0.5 indicators used")
        esg_row = dict(NEUTRAL_ESG)
    esg_result = score_esg(esg_row, parsed["loan_purpose"])
    ratios = compute_ratios(financials)
    revenue = float(financials.get("revenue") or 0)

    fin_result = compute_financial_score(
        ratios,
        sector_for_scoring,
        regional_for_scoring,
        loan_amount,
        revenue,
    )
    audit.append("Deterministic scoring engine executed")

    risk_level = classify_risk(fin_result["financial_score"], esg_result["esg_score"], ratios["leverage_ratio"])
    recommendation = recommend(fin_result["financial_score"], esg_result["esg_score"], risk_level)
    sector_outlook = classify_sector_outlook(
        float(sector_for_scoring.get("economic_performance_index", 1.0))
    )

    sim = simulate_scenario(
        financials,
        esg_row,
        sector_for_scoring,
        regional_for_scoring,
        loan_amount,
        scenario_amount,
        parsed["loan_purpose"],
        interest_rate=SCENARIO_INTEREST_RATE,
    )
    audit.append("Scenario simulation completed")

    drivers = list(dict.fromkeys(fin_result["drivers"] + esg_result["drivers"]))[:5]
    evidence = _build_evidence(regional, sector_data, doc_results)
    confidence = compute_confidence(fin_result["financial_score"], esg_result["esg_score"], len(evidence))

    scenario_payload = {
        **sim["scenario"],
        # The backend has no repayment schedule, so it cannot compute a true
        # DSCR. The old value was an arbitrary tweak of interest coverage;
        # leave it empty rather than show an invented number.
        "dscr": None,
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
        audit,
    )

    return EvaluateResponse(
        company=company,
        loan_amount=loan_amount,
        financial_score=fin_result["financial_score"],
        esg_score=esg_result["esg_score"],
        risk_level=risk_level,
        sector_outlook=sector_outlook,
        recommendation=recommendation,
        confidence=confidence,
        drivers=drivers,
        evidence=evidence,
        audit_trail=audit,
        scenario=scenario,
        summary=summary,
    )


def _load_esg(company_name: str) -> dict[str, Any] | None:
    """ESG indicators for the company, or None when none are on file."""
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
            return None
        cols = [
            "company_id", "company_name", "sector", "environmental_indicator",
            "social_indicator", "governance_indicator", "carbon_exposure",
            "evidence_quality", "esg_evidence_source",
        ]
        return dict(zip(cols, row, strict=False))
    finally:
        conn.close()
