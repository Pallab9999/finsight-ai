"""Qualitative labels for the numbers the dashboard shows.

The dashboard used to print fixed praise next to every metric ("> 1.30x
Covenant", "Ample Cash Cushion", "Pre-Approved at Prime Rates") whatever the
value was, so a 1.07x DSCR was shown as passing a 1.30x covenant and a DECLINE
was badged as pre-approved. These helpers derive the label from the value.

Thresholds mirror the ones the scoring engine and covenant bar already use.
"""

from __future__ import annotations

GOOD = "#10b981"
WATCH = "#fbbf24"
BAD = "#f87171"

DSCR_COVENANT = 1.30
DSCR_FLOOR = 1.00
LEVERAGE_COVENANT = 2.50
FIN_BENCHMARK = 70


def dscr_label(dscr: float) -> tuple[str, str]:
    if dscr >= DSCR_COVENANT:
        return f"Above {DSCR_COVENANT:.2f}x covenant", GOOD
    if dscr >= DSCR_FLOOR:
        return f"Below {DSCR_COVENANT:.2f}x covenant", WATCH
    return f"Below {DSCR_FLOOR:.2f}x floor", BAD


def leverage_label(net_debt_ebitda: float) -> tuple[str, str]:
    if net_debt_ebitda <= LEVERAGE_COVENANT:
        return f"Within {LEVERAGE_COVENANT:.1f}x covenant", GOOD
    if net_debt_ebitda <= 4.0:
        return f"Above {LEVERAGE_COVENANT:.1f}x covenant", WATCH
    return "High leverage", BAD


def margin_label(ebitda_margin_pct: float) -> tuple[str, str]:
    if ebitda_margin_pct >= 15:
        return "Strong margin", GOOD
    if ebitda_margin_pct >= 8:
        return "Moderate margin", WATCH
    return "Thin margin", BAD


def quick_ratio_label(quick_ratio: float) -> tuple[str, str]:
    if quick_ratio >= 1.0:
        return "Cash covers short-term debt", GOOD
    if quick_ratio >= 0.5:
        return "Partial cash cover", WATCH
    return "Thin cash cushion", BAD


def financial_tier_label(score: float) -> tuple[str, str]:
    if score >= FIN_BENCHMARK:
        return f"Above {FIN_BENCHMARK} benchmark", "badge-primary"
    return f"Below {FIN_BENCHMARK} benchmark", "badge-warning"


def esg_tier_label(score: float) -> tuple[str, str]:
    if score >= 75:
        return "High ESG alignment", "badge-success"
    if score >= 50:
        return "Medium ESG alignment", "badge-warning"
    return "Low ESG alignment", "badge-danger"


def outcome_label(recommendation: str) -> tuple[str, str, str]:
    """(badge text, badge class, note) for the bankability outcome card."""
    rec = (recommendation or "").upper()
    if rec == "APPROVE":
        return "Meets approval thresholds", "badge-success", "Prototype rules. Final terms set by the credit committee."
    if rec == "REVIEW":
        return "Needs underwriter review", "badge-warning", "One or more thresholds missed. Review the drivers below."
    return "Below approval thresholds", "badge-danger", "Financial thresholds not met at this amount and tenor."


def verdict_banner(recommendation: str, score: float) -> str:
    """Headline for the underwriter banner, from the deterministic outcome."""
    rec = (recommendation or "REVIEW").upper()
    return f"Deterministic outcome: {rec} (financial score {score:.0f}/100)"


def format_rate(rate: float) -> str:
    """Rates are stored as fractions (0.0525); show them as percentages."""
    pct = rate * 100 if rate < 1 else rate
    return f"{pct:.2f}%"
