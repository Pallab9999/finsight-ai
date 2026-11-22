"""Deterministic scenario simulation."""

from typing import Any

from analytics.esg import score_esg
from analytics.financial import compute_ratios
from analytics.scoring import (
    classify_risk,
    classify_sector_outlook,
    compute_financial_score,
    num,
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
    interest_rate: float = 0.045,
) -> dict[str, Any]:
    """Recalculate scores with a different loan amount.

    The base case is scored exactly as the main assessment scores it. The
    scenario applies the difference to the base loan as extra debt and interest
    (or less of it, when the scenario is smaller), so a smaller loan can never
    score worse than a larger one.
    """
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
        interest_rate=interest_rate,
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
    interest_rate: float = 0.045,
) -> dict[str, Any]:
    adjusted = dict(financials)
    if base_loan_amount is not None and loan_amount != base_loan_amount:
        delta = float(loan_amount - base_loan_amount)
        lt_debt = float(financials.get("long_term_debt") or 0)
        interest = float(financials.get("interest_expense") or 0)
        adjusted["long_term_debt"] = max(0.0, lt_debt + delta)
        adjusted["interest_expense"] = max(0.0, interest + delta * interest_rate)

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
            num(sector_data, "economic_performance_index", 1.0)
        ),
        "drivers": fin["drivers"] + esg["drivers"],
    }
