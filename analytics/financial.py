"""Deterministic financial ratio calculations."""

from typing import Any


def compute_ratios(financials: dict[str, Any]) -> dict[str, float]:
    revenue = float(financials.get("revenue", 0) or 0)
    ebitda = float(financials.get("ebitda", 0) or 0)
    cash = float(financials.get("cash", 0) or 0)
    short_term_debt = float(financials.get("short_term_debt", 0) or 0)
    long_term_debt = float(financials.get("long_term_debt", 0) or 0)
    interest_expense = float(financials.get("interest_expense", 0) or 0)
    revenue_growth = float(financials.get("revenue_growth", 0) or 0)

    total_debt = short_term_debt + long_term_debt
    liquidity_ratio = cash / short_term_debt if short_term_debt > 0 else 2.0
    leverage_ratio = total_debt / revenue if revenue > 0 else 1.0
    interest_coverage = ebitda / interest_expense if interest_expense > 0 else 5.0
    ebitda_margin = ebitda / revenue if revenue > 0 else 0.0

    return {
        "liquidity_ratio": round(liquidity_ratio, 3),
        "leverage_ratio": round(leverage_ratio, 3),
        "interest_coverage": round(interest_coverage, 3),
        "ebitda_margin": round(ebitda_margin, 3),
        "revenue_growth": round(revenue_growth, 3),
        "total_debt": round(total_debt, 2),
    }
