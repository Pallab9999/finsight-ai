"""
FinSight AI - Backend Integration Client & Antifragile Fallback Protocol
========================================================================
Resolution order for each call:
  1. HTTP to FastAPI backend (two-process dev or production)
  2. Local DuckDB deterministic engine (single-process hosting / fallback)
  3. Precomputed mock payload (demo safety net)

Supports multi-company evaluation via company_id.
"""

from __future__ import annotations

import io
import logging
from typing import Any, Dict, Optional, Tuple

import requests

from app.auth import verify_credentials
from app.duckdb_engine import (
    calculate_deterministic_bankability,
    parse_and_ingest_csv,
    parse_and_ingest_pdf,
)
from app.mock_data import calculate_scenario, get_base_demo_payload

logger = logging.getLogger(__name__)

DEFAULT_BACKEND_URL = "http://localhost:8000"


# ------------------------------------------------------------------
# AUTH
# ------------------------------------------------------------------
def authenticate_api(
    email: str,
    password: str,
    role: str = "sme_cfo",
    backend_url: str = DEFAULT_BACKEND_URL,
    force_mock: bool = False,
    timeout_seconds: float = 3.0,
) -> Tuple[Optional[Dict[str, Any]], str, str]:
    if force_mock:
        user, msg = verify_credentials(email, password, role)
        return user, "DETERMINISTIC_FALLBACK", f"Local session verification: {msg}"

    target = f"{backend_url.rstrip('/')}/auth"
    try:
        resp = requests.post(target, json={"email": email, "password": password, "role": role}, timeout=timeout_seconds)
        if resp.status_code == 200:
            return resp.json().get("user"), "LIVE_API", "Authenticated via FastAPI backend."
    except requests.exceptions.RequestException:
        pass

    user, msg = verify_credentials(email, password, role)
    return user, "DETERMINISTIC_FALLBACK", f"Backend unavailable. Local auth: {msg}"


# ------------------------------------------------------------------
# FILE UPLOAD
# ------------------------------------------------------------------
def upload_file_api(
    file_bytes: bytes,
    filename: str,
    doc_type: str,
    company_id: str,
    backend_url: str = DEFAULT_BACKEND_URL,
    force_mock: bool = False,
    timeout_seconds: float = 6.0,
) -> Tuple[Dict[str, Any], str, str]:
    if force_mock:
        return _local_ingest(file_bytes, filename, doc_type, company_id)

    target = f"{backend_url.rstrip('/')}/upload"
    try:
        resp = requests.post(
            target,
            files={"file": (filename, io.BytesIO(file_bytes))},
            data={"doc_type": doc_type, "company_id": company_id},
            timeout=timeout_seconds,
        )
        if resp.status_code in (200, 201):
            return resp.json(), "LIVE_API", f"Ingested '{filename}' via FastAPI."
    except requests.exceptions.RequestException:
        pass

    return _local_ingest(file_bytes, filename, doc_type, company_id)


def _local_ingest(
    file_bytes: bytes, filename: str, doc_type: str, company_id: str
) -> Tuple[Dict[str, Any], str, str]:
    if filename.lower().endswith(".csv"):
        result = parse_and_ingest_csv(file_bytes, filename, company_id)
    else:
        result = parse_and_ingest_pdf(file_bytes, filename, company_id, doc_type)
    return result, "DETERMINISTIC_FALLBACK", f"In-process DuckDB ingestion: {result.get('message', 'Done')}"


# ------------------------------------------------------------------
# EVALUATE
# ------------------------------------------------------------------
def evaluate_application(
    query: str,
    company_id: str = "ecotex",
    loan_amount: int = 750_000,
    backend_url: str = DEFAULT_BACKEND_URL,
    force_mock: bool = False,
    timeout_seconds: float = 8.0,
) -> Tuple[Dict[str, Any], str, str]:
    if force_mock:
        try:
            payload = calculate_deterministic_bankability(company_id=company_id, requested_amount=loan_amount)
            payload["scenario"] = calculate_scenario(payload, loan_amount + 250_000)
            return payload, "DETERMINISTIC_FALLBACK", "Operating in deterministic DuckDB mode."
        except Exception:
            return get_base_demo_payload(), "DETERMINISTIC_FALLBACK", "Mock fallback."

    target = f"{backend_url.rstrip('/')}/evaluate"
    try:
        resp = requests.post(
            target,
            json={"query": query, "company_id": company_id, "loan_amount": loan_amount},
            timeout=timeout_seconds,
        )
        if resp.status_code == 200:
            data = resp.json()
            if "scenario" not in data:
                data["scenario"] = calculate_scenario(data, loan_amount + 250_000)
            return data, "LIVE_API", f"Evaluated via FastAPI ({target})."
    except requests.exceptions.RequestException:
        pass

    try:
        payload = calculate_deterministic_bankability(company_id=company_id, requested_amount=loan_amount)
        payload["scenario"] = calculate_scenario(payload, loan_amount + 250_000)
        return payload, "IN_PROCESS", "Backend unreachable. Evaluated via in-process DuckDB engine."
    except Exception:
        return get_base_demo_payload(), "DETERMINISTIC_FALLBACK", "All pipelines failed. Mock fallback."


# ------------------------------------------------------------------
# SCENARIO SIMULATION
# ------------------------------------------------------------------
def simulate_scenario_api(
    company_id: str,
    requested_amount: int,
    base_payload: Dict[str, Any],
    backend_url: str = DEFAULT_BACKEND_URL,
    force_mock: bool = False,
    timeout_seconds: float = 3.0,
) -> Tuple[Dict[str, Any], str, str]:
    if force_mock:
        res = calculate_scenario(base_payload, requested_amount)
        return res, "DETERMINISTIC_FALLBACK", "Simulated via deterministic formulas."

    target = f"{backend_url.rstrip('/')}/scenario"
    try:
        resp = requests.post(
            target,
            json={"company_id": company_id, "loan_amount": requested_amount},
            timeout=timeout_seconds,
        )
        if resp.status_code == 200:
            return resp.json(), "LIVE_API", "Simulated via FastAPI."
    except requests.exceptions.RequestException:
        pass

    res = calculate_scenario(base_payload, requested_amount)
    return res, "DETERMINISTIC_FALLBACK", "Backend unreachable. Local simulation."
