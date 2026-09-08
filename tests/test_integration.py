"""Basic integration tests for FinSight AI."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.agent import evaluate_request, parse_query
from backend.fallback import get_fallback_response, is_magic_query
from backend.tools import get_company_financials, get_regional_risk, get_sector_performance
from ingestion.loaders import seed_database
from rag.retrieval import search_documents


@pytest.fixture(scope="module", autouse=True)
def setup_db(tmp_path_factory):
    db_path = ROOT / "data" / "finsight.duckdb"
    seed_database(db_path)
    return db_path


def test_parse_query():
    parsed = parse_query(
        "Assess a €750k sustainability-linked equipment loan for EcoTex Milano, a textile manufacturer in Milan."
    )
    assert "ecotex" in parsed["company"].lower()
    assert parsed["loan_amount"] == 750_000


def test_company_financials():
    result = get_company_financials("EcoTex Milano")
    assert "error" not in result
    assert result["company_name"] == "EcoTex Milano"
    assert "ratios" in result


def test_regional_risk():
    result = get_regional_risk("Milano")
    assert "error" not in result
    assert result["province"] == "Milano"


def test_sector_performance():
    result = get_sector_performance("Milano", "Textile Manufacturing")
    assert "error" not in result


def test_document_search():
    results = search_documents("sustainability water recycling", company_name="EcoTex Milano")
    assert len(results) > 0


def test_evaluate_request():
    result = evaluate_request(
        "Assess a €750k sustainability-linked equipment loan for EcoTex Milano, a textile manufacturer in Milan."
    )
    assert result.financial_score > 0
    assert result.esg_score > 0
    assert result.recommendation in ("APPROVE", "REVIEW", "DECLINE")
    assert len(result.audit_trail) >= 5


def test_magic_string_fallback():
    assert is_magic_query(
        "Assess a €750k sustainability-linked equipment loan for EcoTex Milano, a textile manufacturer in Milan."
    )
    fallback = get_fallback_response()
    assert fallback.company == "EcoTex Milano"
