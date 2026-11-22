"""Regression tests for the hardening pass on the assessment pipeline."""

import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from analytics.amounts import parse_amount
from analytics.esg import score_esg
from analytics.scenario import simulate_scenario
from analytics.scoring import compute_financial_score, num
from app.api_client import parse_query_fields
from backend import agent
from backend.agent import CompanyNotFoundError, default_scenario_amount, evaluate_request, parse_query
from backend.main import app

DEMO = "Assess a €750k sustainability-linked equipment loan for EcoTex Milano, a textile manufacturer in Milan."


# ── Amount parsing ──────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Assess a €750k loan", 750_000),
        ("Assess a €1M loan", 1_000_000),
        ("€1.5m facility", 1_500_000),
        ("€1.2 million loan", 1_200_000),
        ("1,5 milioni di euro", 1_500_000),
        ("€750,000 loan", 750_000),
        ("€ 750.000", 750_000),
        ("EUR 2.000.000", 2_000_000),
        ("750000 EUR", 750_000),
        ("€750", 750_000),
    ],
)
def test_parse_amount_formats(text, expected):
    assert parse_amount(text) == expected


@pytest.mark.parametrize("text", ["In 2025, assess a loan", "3 machines over 5 months", "", None])
def test_parse_amount_ignores_bare_numbers(text):
    assert parse_amount(text) is None


def test_backend_and_ui_parsers_agree():
    for text in ("Assess a €1M loan for Meccanica Precisione Varese", "€1.2 million for AgroBio Brianza"):
        assert parse_query(text)["loan_amount"] == parse_query_fields(text)[1]


# ── Company identification ──────────────────────────────────────────────────

def test_unknown_company_is_not_silently_ecotex():
    assert parse_query("Evaluate Rossi Spa loan of 500k")["company"] is None
    with pytest.raises(CompanyNotFoundError):
        evaluate_request("Evaluate Rossi Spa loan of 500k")


def test_unknown_company_id_is_rejected():
    with pytest.raises(CompanyNotFoundError):
        evaluate_request(DEMO, company_id="nope")


def test_api_returns_404_for_unknown_company():
    client = TestClient(app)
    resp = client.post("/evaluate", json={"query": "Assess a €500k loan for Rossi Spa in Bergamo."})
    assert resp.status_code == 404
    assert "Rossi Spa" in resp.json()["detail"]["message"]


# ── Audit trail isolation ───────────────────────────────────────────────────

def test_audit_trail_is_per_request():
    assert not hasattr(agent, "AUDIT_TRAIL")
    results, errors = {}, []

    def run(cid):
        try:
            results[cid] = evaluate_request(DEMO, company_id=cid)
        except Exception as exc:  # surface thread failures to the test
            errors.append(repr(exc))

    threads = [threading.Thread(target=run, args=(cid,)) for cid in ("ecotex", "meccanica", "agrobio")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    assert set(results) == {"ecotex", "meccanica", "agrobio"}
    for res in results.values():
        assert res.audit_trail.count("Query parsed") == 1
        assert res.audit_trail.count("Deterministic scoring engine executed") == 1


# ── Zero values are data, not "missing" ────────────────────────────────────

def test_num_keeps_real_zero():
    assert num({"x": 0}, "x", 0.5) == 0.0
    assert num({"x": None}, "x", 0.5) == 0.5
    assert num({}, "x", 0.5) == 0.5
    assert num({"x": "bad"}, "x", 0.5) == 0.5


def test_zero_default_rate_scores_better_than_two_percent():
    ratios = {"liquidity_ratio": 1.2, "leverage_ratio": 0.6, "revenue_growth": 0.05}
    sector = {"economic_performance_index": 1.0}
    zero = compute_financial_score(ratios, sector, {"liquidity_indicator": 0.8, "loan_default_rate": 0.0}, 500_000, 10_000_000)
    two = compute_financial_score(ratios, sector, {"liquidity_indicator": 0.8, "loan_default_rate": 0.02}, 500_000, 10_000_000)
    assert zero["components"]["regional"] > two["components"]["regional"]


def test_zero_carbon_exposure_is_not_penalised():
    base = {"environmental_indicator": 0.8, "social_indicator": 0.7, "governance_indicator": 0.7, "evidence_quality": 0.8}
    zero = score_esg({**base, "carbon_exposure": 0.0}, "equipment")
    half = score_esg({**base, "carbon_exposure": 0.5}, "equipment")
    assert zero["esg_score"] > half["esg_score"]


# ── Scenario engine ─────────────────────────────────────────────────────────

FIN = {
    "revenue": 5_000_000, "ebitda": 700_000, "cash": 600_000, "short_term_debt": 500_000,
    "long_term_debt": 1_500_000, "interest_expense": 90_000, "revenue_growth": 0.05,
}
ESG = {"environmental_indicator": 0.7, "social_indicator": 0.7, "governance_indicator": 0.7,
       "carbon_exposure": 0.3, "evidence_quality": 0.8}
SECTOR = {"economic_performance_index": 1.0}
REGION = {"liquidity_indicator": 0.8, "loan_default_rate": 0.02}


def _scenario_score(base, scen):
    return simulate_scenario(FIN, ESG, SECTOR, REGION, base, scen)["scenario"]["financial_score"]


def test_scenario_is_monotonic_in_loan_amount():
    base = 1_000_000
    scores = [_scenario_score(base, amt) for amt in (200_000, 600_000, 1_000_000, 1_400_000, 2_000_000)]
    assert scores == sorted(scores, reverse=True)


def test_smaller_scenario_reduces_debt_not_just_penalty():
    base = 1_500_000
    smaller = simulate_scenario(FIN, ESG, SECTOR, REGION, base, 500_000)
    assert smaller["scenario"]["financial_score"] >= smaller["base"]["financial_score"]


def test_scenario_at_base_amount_matches_base():
    res = simulate_scenario(FIN, ESG, SECTOR, REGION, 750_000, 750_000)
    assert res["scenario"]["financial_score"] == res["base"]["financial_score"]


def test_default_scenario_amount_is_a_real_stress_case():
    assert default_scenario_amount(750_000) == 1_000_000
    assert default_scenario_amount(1_500_000) == 2_000_000
    assert default_scenario_amount(1_000_000) > 1_000_000


def test_large_loan_scenario_is_larger_and_summary_wording_matches():
    res = evaluate_request("Assess a €1.5M equipment loan for Meccanica Precisione Varese")
    assert res.loan_amount == 1_500_000
    assert res.scenario.loan_amount > res.loan_amount
    assert "Reducing" not in res.summary


def test_scenario_dscr_is_not_invented():
    res = evaluate_request(DEMO)
    assert res.scenario.dscr is None
