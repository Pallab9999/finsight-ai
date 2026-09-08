"""Resolution order of the UI's evaluation client."""

import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import api_client
from ingestion.loaders import seed_database

DEMO = "Assess a €750k sustainability-linked equipment loan for EcoTex Milano, a textile manufacturer in Milan."


def test_force_mock_returns_precomputed():
    payload, mode, _ = api_client.evaluate_application(DEMO, force_mock=True)

    assert mode == "DETERMINISTIC_FALLBACK"
    assert payload["company"] == "EcoTex Milano"


def test_unreachable_backend_falls_back_to_in_process():
    """This is the path used by single-process hosting."""
    seed_database(ROOT / "data" / "finsight.duckdb")

    payload, mode, status = api_client.evaluate_application(
        DEMO,
        backend_url="http://127.0.0.1:9",  # discard port, always refuses
        timeout_seconds=2.0,
    )

    assert mode == "IN_PROCESS"
    assert "in-process" in status
    assert payload["financial_score"] > 0
    assert payload["scenario"]["recommendation"] in ("APPROVE", "REVIEW", "DECLINE")


def test_in_process_result_carries_ui_keys():
    seed_database(ROOT / "data" / "finsight.duckdb")

    payload, mode, _ = api_client.evaluate_application(
        DEMO,
        backend_url="http://127.0.0.1:9",
        timeout_seconds=2.0,
    )

    assert mode == "IN_PROCESS"
    assert "dscr" in payload["scenario"]
    assert all("category" in item for item in payload["evidence"])


def test_precomputed_payload_when_pipeline_unavailable(monkeypatch):
    monkeypatch.setattr(api_client, "_evaluate_in_process", lambda *a, **k: None)

    payload, mode, _ = api_client.evaluate_application(
        DEMO,
        backend_url="http://127.0.0.1:9",
        timeout_seconds=2.0,
    )

    assert mode == "DETERMINISTIC_FALLBACK"
    assert payload["company"] == "EcoTex Milano"
