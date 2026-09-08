"""Pydantic contracts for the FinSight API."""

from typing import Literal

from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    query: str = Field(..., min_length=3)
    loan_amount: int | None = Field(default=None, ge=100_000, le=5_000_000)
    scenario_loan_amount: int | None = Field(default=None, ge=100_000, le=5_000_000)


class EvidenceItem(BaseModel):
    source: str
    claim: str
    category: str = "FACT"


class ScenarioResult(BaseModel):
    loan_amount: int
    financial_score: int
    esg_score: int
    risk_level: Literal["Low", "Medium", "High"]
    recommendation: Literal["APPROVE", "REVIEW", "DECLINE"]
    dscr: float | None = None
    summary: str | None = None


class EvaluateResponse(BaseModel):
    company: str
    loan_amount: int
    financial_score: int
    esg_score: int
    risk_level: Literal["Low", "Medium", "High"]
    sector_outlook: Literal["Positive", "Neutral", "Negative"]
    recommendation: Literal["APPROVE", "REVIEW", "DECLINE"]
    confidence: float = Field(ge=0.0, le=1.0)
    drivers: list[str]
    evidence: list[EvidenceItem]
    audit_trail: list[str]
    scenario: ScenarioResult
    summary: str


class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    message: str
    fallback_available: bool = False
