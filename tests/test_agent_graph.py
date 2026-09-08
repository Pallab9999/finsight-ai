"""Test LangGraph wrapper and error paths."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.agent_graph import evaluate_with_graph
from backend.fallback import get_fallback_response, is_magic_query
from ingestion.loaders import seed_database


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    seed_database(ROOT / "data" / "finsight.duckdb")


def test_langgraph_evaluate():
    result = evaluate_with_graph(
        "Assess a €750k sustainability-linked equipment loan for EcoTex Milano, a textile manufacturer in Milan."
    )
    assert result.recommendation in ("APPROVE", "REVIEW", "DECLINE")
    assert result.scenario.loan_amount == 1_000_000


def test_magic_string_detection():
    assert is_magic_query(
        "Assess a €750k sustainability-linked equipment loan for EcoTex Milano, a textile manufacturer in Milan."
    )


def test_fallback_response_valid():
    fb = get_fallback_response()
    assert fb.company == "EcoTex Milano"
    assert fb.scenario.recommendation == "REVIEW"
