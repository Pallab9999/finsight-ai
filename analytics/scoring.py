"""Deterministic financial health scoring and recommendation engine."""

from typing import Any, Literal


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def score_liquidity(liquidity_ratio: float) -> float:
    if liquidity_ratio >= 1.5:
        return 90
    if liquidity_ratio >= 1.0:
        return 75
    if liquidity_ratio >= 0.7:
        return 55
    return 30


def score_leverage(leverage_ratio: float) -> float:
    if leverage_ratio <= 0.5:
        return 90
    if leverage_ratio <= 0.8:
        return 75
    if leverage_ratio <= 1.2:
        return 55
    return 30


def score_growth(revenue_growth: float) -> float:
    if revenue_growth >= 0.08:
        return 90
    if revenue_growth >= 0.03:
        return 75
    if revenue_growth >= 0.0:
        return 55
    return 35


def score_sector(sector_index: float) -> float:
    if sector_index >= 1.05:
        return 85
    if sector_index >= 0.98:
        return 70
    if sector_index >= 0.90:
        return 50
    return 35


def score_regional(liquidity_indicator: float, default_rate: float) -> float:
    base = liquidity_indicator * 100
    penalty = default_rate * 500
    return _clamp(base - penalty)


def compute_financial_score(
    ratios: dict[str, float],
    sector_data: dict[str, Any],
    regional_data: dict[str, Any],
    loan_amount: int,
    revenue: float,
) -> dict[str, Any]:
    liquidity = score_liquidity(ratios.get("liquidity_ratio", 1.0))
    leverage = score_leverage(ratios.get("leverage_ratio", 0.8))
    growth = score_growth(ratios.get("revenue_growth", 0.0))

    sector_index = float(sector_data.get("economic_performance_index", 1.0) or 1.0)
    sector = score_sector(sector_index)

    regional_liq = float(regional_data.get("liquidity_indicator", 0.75) or 0.75)
    default_rate = float(regional_data.get("loan_default_rate", 0.02) or 0.02)
    regional = score_regional(regional_liq, default_rate)

    loan_burden = loan_amount / revenue if revenue > 0 else 1.0
    loan_penalty = 0
    if loan_burden > 0.40:
        loan_penalty = 18
    elif loan_burden > 0.28:
        loan_penalty = 12
    elif loan_burden > 0.20:
        loan_penalty = 6
    elif loan_burden > 0.15:
        loan_penalty = 2

    raw_score = (
        0.25 * liquidity
        + 0.25 * leverage
        + 0.20 * growth
        + 0.15 * sector
        + 0.15 * regional
    )
    financial_score = int(_clamp(raw_score - loan_penalty))

    drivers = []
    if liquidity >= 75:
        drivers.append(f"Strong liquidity position (cash/ST debt: {ratios.get('liquidity_ratio', 0):.2f}x)")
    elif liquidity < 55:
        drivers.append("Liquidity position below comfortable threshold")

    if growth >= 75:
        drivers.append(f"Positive revenue trajectory ({ratios.get('revenue_growth', 0)*100:.1f}% YoY)")
    if sector >= 70:
        drivers.append("Favourable sector conditions in the region")
    if regional >= 70:
        drivers.append("Regional credit conditions support the assessment")
    if leverage < 55:
        drivers.append("Elevated leverage increases financial risk")
    if loan_penalty > 0:
        drivers.append(f"Loan-to-revenue ratio ({loan_burden:.0%}) adds financing burden")

    return {
        "financial_score": financial_score,
        "drivers": drivers[:5],
        "components": {
            "liquidity": liquidity,
            "leverage": leverage,
            "growth": growth,
            "sector": sector,
            "regional": regional,
            "loan_penalty": loan_penalty,
        },
    }


def classify_risk(financial_score: int, esg_score: int, leverage_ratio: float) -> Literal["Low", "Medium", "High"]:
    if financial_score >= 80 and esg_score >= 75 and leverage_ratio <= 0.75:
        return "Low"
    if financial_score < 55 or leverage_ratio > 1.0:
        return "High"
    if financial_score < 72 or leverage_ratio > 0.85:
        return "High" if financial_score < 65 else "Medium"
    return "Medium"


def classify_sector_outlook(sector_index: float) -> Literal["Positive", "Neutral", "Negative"]:
    if sector_index >= 1.03:
        return "Positive"
    if sector_index >= 0.95:
        return "Neutral"
    return "Negative"


def recommend(
    financial_score: int,
    esg_score: int,
    risk_level: str,
    critical_flag: bool = False,
) -> Literal["APPROVE", "REVIEW", "DECLINE"]:
    if critical_flag or financial_score < 55:
        return "DECLINE"
    if financial_score >= 75 and esg_score >= 70 and risk_level == "Low":
        return "APPROVE"
    if financial_score >= 78 and esg_score >= 70 and risk_level == "Medium":
        return "APPROVE"
    if financial_score >= 55:
        return "REVIEW"
    return "DECLINE"


def compute_confidence(
    financial_score: int,
    esg_score: int,
    evidence_count: int,
) -> float:
    base = 0.5 + (financial_score + esg_score) / 400
    evidence_boost = min(0.15, evidence_count * 0.05)
    return round(min(0.95, base + evidence_boost), 2)
