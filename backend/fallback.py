"""Magic String fallback for demo reliability."""

from backend.config import DEMO_QUERY
from backend.schemas import EvaluateResponse, EvidenceItem, ScenarioResult

FALLBACK_RESPONSE = EvaluateResponse(
    company="EcoTex Milano",
    loan_amount=750_000,
    financial_score=80,
    esg_score=86,
    risk_level="Low",
    sector_outlook="Positive",
    recommendation="APPROVE",
    confidence=0.87,
    drivers=[
        "Positive revenue trajectory (+8.2% YoY)",
        "Favourable sector conditions in Lombardia textile manufacturing",
        "Strong project ESG alignment with water-recycling equipment",
        "Adequate liquidity with cash coverage of 1.4x short-term debt",
    ],
    evidence=[
        EvidenceItem(
            source="Banca d'Italia",
            claim="Regional credit conditions in Lombardia support SME lending with stable liquidity indicators.",
        ),
        EvidenceItem(
            source="Open Data Lombardia",
            claim="Textile manufacturing sector shows positive turnover growth in the Milano province.",
        ),
        EvidenceItem(
            source="EcoTex Sustainability Report 2025",
            claim="Company committed to 40% water reduction via new recycling equipment, aligned with EU Taxonomy.",
        ),
    ],
    audit_trail=[
        "Company financials queried",
        "Regional risk queried",
        "Sector performance queried",
        "ESG evidence retrieved",
        "Deterministic scoring engine executed",
        "Scenario simulation completed",
    ],
    scenario=ScenarioResult(
        loan_amount=1_000_000,
        financial_score=76,
        esg_score=86,
        risk_level="Medium",
        recommendation="REVIEW",
    ),
    summary=(
        "The application is financially supportable under the base case, with strong ESG alignment "
        "for sustainability-linked equipment financing. Increasing financing to €1M materially "
        "increases leverage and shifts the recommendation to REVIEW."
    ),
)


def is_magic_query(query: str) -> bool:
    normalized = " ".join(query.lower().split())
    magic = " ".join(DEMO_QUERY.lower().split())
    return normalized == magic or (
        "ecotex milano" in normalized
        and "750" in normalized
        and ("sustainability" in normalized or "equipment" in normalized)
    )


def get_fallback_response() -> EvaluateResponse:
    return FALLBACK_RESPONSE.model_copy(deep=True)
