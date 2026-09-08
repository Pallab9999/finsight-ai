"""Deterministic ESG scoring."""

from typing import Any


def score_esg(esg_data: dict[str, Any], loan_purpose: str = "") -> dict[str, Any]:
    environmental = float(esg_data.get("environmental_indicator", 0) or 0)
    social = float(esg_data.get("social_indicator", 0) or 0)
    governance = float(esg_data.get("governance_indicator", 0) or 0)
    carbon_exposure = float(esg_data.get("carbon_exposure", 0.5) or 0.5)
    evidence_quality = float(esg_data.get("evidence_quality", 0.7) or 0.7)

    purpose_lower = loan_purpose.lower()
    project_alignment = 0.85
    if any(k in purpose_lower for k in ("sustainability", "green", "energy", "recycling", "esg")):
        project_alignment = 0.95
    elif any(k in purpose_lower for k in ("expansion", "working capital")):
        project_alignment = 0.6

    transition_potential = max(0.0, min(1.0, 1.0 - carbon_exposure + 0.2))

    environmental_score = environmental * 100
    project_score = project_alignment * 100
    transition_score = transition_potential * 100
    evidence_score = evidence_quality * 100

    esg_score = int(
        0.50 * environmental_score
        + 0.25 * project_score
        + 0.15 * transition_score
        + 0.10 * evidence_score
    )
    esg_score = max(0, min(100, esg_score))

    if esg_score >= 75:
        esg_level = "High"
    elif esg_score >= 50:
        esg_level = "Medium"
    else:
        esg_level = "Low"

    drivers = []
    if environmental >= 0.7:
        drivers.append("Strong environmental performance indicators")
    if project_alignment >= 0.9:
        drivers.append("Financing purpose strongly aligned with sustainability goals")
    if transition_potential >= 0.6:
        drivers.append("Positive transition potential for lower carbon exposure")
    if evidence_quality >= 0.7:
        drivers.append("Documented ESG evidence supports the assessment")
    if social >= 0.7:
        drivers.append("Solid social responsibility indicators")
    if governance >= 0.7:
        drivers.append("Governance practices meet expected standards")

    return {
        "esg_score": esg_score,
        "esg_level": esg_level,
        "drivers": drivers[:5],
        "components": {
            "environmental": round(environmental_score, 1),
            "project_alignment": round(project_score, 1),
            "transition": round(transition_score, 1),
            "evidence": round(evidence_score, 1),
        },
    }
