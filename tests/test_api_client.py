"""Resolution order of the UI's evaluation client (multi-company version)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import api_client
from app.duckdb_engine import get_connection

DEMO = "Assess a EUR 750k sustainability-linked equipment loan for EcoTex Milano."


def test_prompt_loan_amount_changes_score():
    small, _, _ = api_client.evaluate_application(
        "Assess a EUR 400k loan for EcoTex Milano.",
        company_id="ecotex",
        force_mock=True,
    )
    large, _, _ = api_client.evaluate_application(
        "Assess a EUR 5000k loan for EcoTex Milano.",
        company_id="ecotex",
        force_mock=True,
    )

    assert small["loan_amount"] == 400_000
    assert large["loan_amount"] == 5_000_000
    assert large["financial_score"] < small["financial_score"]


def test_parse_query_fields_extracts_company_and_amount():
    cid, amt = api_client.parse_query_fields(
        "Assess a €500k facility for Meccanica Precisione Varese."
    )
    assert cid == "meccanica"
    assert amt == 500_000


def test_force_mock_returns_deterministic_duckdb():
    payload, mode, _ = api_client.evaluate_application(DEMO, company_id="ecotex", force_mock=True)

    assert mode == "DETERMINISTIC_FALLBACK"
    assert "EcoTex" in payload["company"]
    assert payload["financial_score"] > 0
    assert payload["recommendation"] in ("APPROVE", "REVIEW", "DECLINE")


def test_multi_company_evaluation_produces_different_scores():
    eco, _, _ = api_client.evaluate_application(
        "Assess a EUR 750k loan for EcoTex Milano.", company_id="ecotex", force_mock=True
    )
    mec, _, _ = api_client.evaluate_application(
        "Assess a EUR 500k loan for Meccanica Precisione Varese.", company_id="meccanica", force_mock=True
    )
    agro, _, _ = api_client.evaluate_application(
        "Assess a EUR 400k loan for AgroBio Brianza.", company_id="agrobio", force_mock=True
    )

    assert eco["financial_score"] != mec["financial_score"]
    assert eco["company"] != mec["company"]
    assert mec["company"] != agro["company"]


def test_unreachable_backend_falls_back_to_in_process():
    payload, mode, status = api_client.evaluate_application(
        DEMO,
        company_id="ecotex",
        backend_url="http://127.0.0.1:9",
        timeout_seconds=2.0,
    )

    assert mode == "IN_PROCESS"
    assert payload["financial_score"] > 0
    assert payload["scenario"]["recommendation"] in ("APPROVE", "REVIEW", "DECLINE")


def test_scenario_produces_different_outcome():
    eco, _, _ = api_client.evaluate_application(DEMO, company_id="ecotex", loan_amount=750_000, force_mock=True)

    assert "scenario" in eco
    assert eco["scenario"]["loan_amount"] == 1_000_000
    assert eco["scenario"]["recommendation"] in ("APPROVE", "REVIEW", "DECLINE")


def test_csv_upload_ingests_and_changes_score():
    csv_data = (
        b"fiscal_year;revenue;ebitda;net_income;total_assets;net_equity;total_debt;"
        b"short_term_debt;cash_and_equivalents;capex\n"
        b"2025;20000000;3800000;1700000;18000000;8500000;5200000;1300000;2500000;1100000\n"
    )

    result, mode, _ = api_client.upload_file_api(
        csv_data, "strong_balance.csv", "FINANCIAL_STATEMENT", "meccanica", force_mock=True
    )

    assert result["status"] == "SUCCESS"
    assert result["fiscal_year"] == 2025

    payload, _, _ = api_client.evaluate_application(
        "Assess a EUR 500k loan for Meccanica Precisione Varese.",
        company_id="meccanica",
        force_mock=True,
    )
    assert payload["financial_score"] > 0


def test_auth_returns_user_on_valid_credentials():
    user, mode, msg = api_client.authenticate_api(
        "cfo@ecotex.it", "cfo2026", "sme_borrower", force_mock=True
    )

    assert user is not None
    assert user["name"] == "Marco Valenti"
    assert "EcoTex" in user["organization"]
