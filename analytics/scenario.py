"""Deterministic scenario simulation."""

from typing import Any

from analytics.esg import score_esg
from analytics.financial import compute_ratios
from analytics.scoring import (
    classify_risk,
    classify_sector_outlook,
    compute_financial_score,
    recommend,
)


def simulate_scenario(
    financials: dict[str, Any],
    esg_data: dict[str, Any],
    sector_data: dict[str, Any],
    regional_data: dict[str, Any],
    base_loan_amount: int,
    scenario_loan_amount: int,
    loan_purpose: str = "",
) -> dict[str, Any]:
    """Recalculate scores with a different loan amount."""
    ratios = compute_ratios(financials)
    revenue = float(financials.get("revenue", 0) or 0)

    base_result = _evaluate(
        financials, esg_data, sector_data, regional_data, base_loan_amount, loan_purpose
    )
    scenario_result = _evaluate(
        financials,
        esg_data,
        sector_data,
        regional_data,
        scenario_loan_amount,
        loan_purpose,
        base_loan_amount=base_loan_amount,
    )

    return {
        "base": base_result,
        "scenario": {
            "loan_amount": scenario_loan_amount,
            "financial_score": scenario_result["financial_score"],
            "esg_score": scenario_result["esg_score"],
            "risk_level": scenario_result["risk_level"],
            "recommendation": scenario_result["recommendation"],
        },
        "delta": {
            "financial_score": scenario_result["financial_score"] - base_result["financial_score"],
            "risk_change": f"{base_result['risk_level']} -> {scenario_result['risk_level']}",
            "recommendation_change": f"{base_result['recommendation']} -> {scenario_result['recommendation']}",
        },
    }


def _evaluate(
    financials: dict[str, Any],
    esg_data: dict[str, Any],
    sector_data: dict[str, Any],
    regional_data: dict[str, Any],
    loan_amount: int,
    loan_purpose: str,
    base_loan_amount: int | None = None,
) -> dict[str, Any]:
    adjusted = dict(financials)
    if base_loan_amount is not None and loan_amount > base_loan_amount:
        extra_debt = float(loan_amount - base_loan_amount)
        adjusted["long_term_debt"] = float(financials.get("long_term_debt", 0) or 0) + extra_debt
        adjusted["interest_expense"] = float(financials.get("interest_expense", 0) or 0) + extra_debt * 0.045

    ratios = compute_ratios(adjusted)
    revenue = float(adjusted.get("revenue", 0) or 0)

    fin = compute_financial_score(ratios, sector_data, regional_data, loan_amount, revenue)
    esg = score_esg(esg_data, loan_purpose)
    risk = classify_risk(fin["financial_score"], esg["esg_score"], ratios["leverage_ratio"])
    rec = recommend(fin["financial_score"], esg["esg_score"], risk)

    return {
        "financial_score": fin["financial_score"],
        "esg_score": esg["esg_score"],
        "risk_level": risk,
        "recommendation": rec,
        "sector_outlook": classify_sector_outlook(
            float(sector_data.get("economic_performance_index", 1.0) or 1.0)
        ),
        "drivers": fin["drivers"] + esg["drivers"],
    }
