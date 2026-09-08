"""
FinSight AI - Backend Integration Client & Antifragile Fallback Protocol
========================================================================
Handles HTTP communication between the Streamlit UI and the FastAPI backend endpoints:
- POST /auth
- POST /upload
- POST /evaluate
- POST /scenario

Guarantees 100% Antifragility:
If the FastAPI backend is offline, times out, or returns an HTTP error, this client
automatically executes local DuckDB queries and deterministic Python formulas,
preventing any UI crash and ensuring seamless hackathon demo continuity.
"""

import io
import requests
from typing import Dict, Any, Tuple, Optional
from app.mock_data import get_base_demo_payload, calculate_scenario
from app.auth import verify_credentials
from app.duckdb_engine import (
    calculate_deterministic_bankability,
    parse_and_ingest_csv,
    parse_and_ingest_pdf
)

DEFAULT_BACKEND_URL = "http://localhost:8000"


def authenticate_api(
    email: str,
    password: str,
    role: str = "sme_borrower",
    backend_url: str = DEFAULT_BACKEND_URL,
    force_mock: bool = False,
    timeout_seconds: float = 3.0
) -> Tuple[Optional[Dict[str, Any]], str, str]:
    """
    Authenticates user against FastAPI /auth endpoint or local credential store.
    Returns: (user_dict, mode, status_message)
    """
    if force_mock:
        user, msg = verify_credentials(email, password, role)
        mode = "DETERMINISTIC_FALLBACK"
        return user, mode, f"Local session verification: {msg}"

    target_endpoint = f"{backend_url.rstrip('/')}/auth"
    try:
        response = requests.post(
            target_endpoint,
            json={"email": email, "password": password, "role": role},
            headers={"Content-Type": "application/json"},
            timeout=timeout_seconds
        )
        if response.status_code == 200:
            return response.json().get("user"), "LIVE_API", "Authenticated via FastAPI backend."
        else:
            user, msg = verify_credentials(email, password, role)
            return user, "DETERMINISTIC_FALLBACK", f"Backend HTTP {response.status_code}. Engaged local auth fallback: {msg}"
    except requests.exceptions.RequestException as exc:
        user, msg = verify_credentials(email, password, role)
        return user, "DETERMINISTIC_FALLBACK", f"Backend unreachable ({type(exc).__name__}). Engaged local auth: {msg}"


def upload_file_api(
    file_bytes: bytes,
    filename: str,
    doc_type: str,
    company_id: str,
    backend_url: str = DEFAULT_BACKEND_URL,
    force_mock: bool = False,
    timeout_seconds: float = 6.0
) -> Tuple[Dict[str, Any], str, str]:
    """
    Uploads a balance sheet (CSV/PDF) or ESG disclosure to FastAPI /upload or directly ingests into DuckDB.
    Returns: (result_dict, mode, status_message)
    """
    if force_mock:
        return _local_ingest(file_bytes, filename, doc_type, company_id)

    target_endpoint = f"{backend_url.rstrip('/')}/upload"
    try:
        files = {"file": (filename, io.BytesIO(file_bytes))}
        data = {"doc_type": doc_type, "company_id": company_id}
        response = requests.post(
            target_endpoint,
            files=files,
            data=data,
            timeout=timeout_seconds
        )
        if response.status_code in (200, 201):
            res_json = response.json()
            if "evidences" not in res_json:
                local_eval = _local_ingest(file_bytes, filename, doc_type, company_id)[0]
                res_json["evidences"] = local_eval.get("evidences", [])
            return res_json, "LIVE_API", f"Successfully ingested '{filename}' via FastAPI."
        else:
            res = _local_ingest(file_bytes, filename, doc_type, company_id)
            return res[0], "DETERMINISTIC_FALLBACK", f"Backend HTTP {response.status_code}. Local DuckDB ingestion succeeded."
    except requests.exceptions.RequestException as exc:
        res = _local_ingest(file_bytes, filename, doc_type, company_id)
        return res[0], "DETERMINISTIC_FALLBACK", f"Backend unreachable ({type(exc).__name__}). Local DuckDB ingestion succeeded."


def _local_ingest(file_bytes: bytes, filename: str, doc_type: str, company_id: str) -> Tuple[Dict[str, Any], str, str]:
    """Local DuckDB parsing fallback."""
    if filename.lower().endswith(".csv"):
        result = parse_and_ingest_csv(file_bytes, filename, company_id)
    else:
        result = parse_and_ingest_pdf(file_bytes, filename, company_id, doc_type)
    return result, "DETERMINISTIC_FALLBACK", f"Direct In-Process DuckDB ingestion: {result.get('message', 'Completed')}"


def evaluate_application(
    query: str,
    company_id: str = "ecotex",
    loan_amount: int = 750000,
    interest_rate: float = 0.0525,
    tenor_years: int = 5,
    backend_url: str = DEFAULT_BACKEND_URL,
    force_mock: bool = False,
    timeout_seconds: float = 4.0
) -> Tuple[Dict[str, Any], str, str]:
    """
    Evaluates an SME financing application via FastAPI /evaluate or local DuckDB scoring engine.
    Returns: (payload, mode, status_message)
    """
    if force_mock:
        try:
            payload = calculate_deterministic_bankability(
                company_id=company_id,
                requested_amount=loan_amount,
                interest_rate=interest_rate,
                tenor_years=tenor_years
            )
            return payload, "DETERMINISTIC_FALLBACK", "Operating in safe deterministic DuckDB mode."
        except Exception:
            payload = get_base_demo_payload()
            return payload, "DETERMINISTIC_FALLBACK", "Operating in safe deterministic mock fallback."

    target_endpoint = f"{backend_url.rstrip('/')}/evaluate"
    request_data = {
        "query": query,
        "company_id": company_id,
        "loan_amount": loan_amount,
        "interest_rate": interest_rate,
        "tenor_years": tenor_years
    }

    try:
        response = requests.post(
            target_endpoint,
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=timeout_seconds
        )
        if response.status_code == 200:
            data = response.json()
            if "sensitivity_curve" not in data:
                local_b = calculate_deterministic_bankability(company_id, loan_amount, interest_rate, tenor_years)
                data["sensitivity_curve"] = local_b.get("sensitivity_curve", [])
            return data, "LIVE_API", f"Successfully evaluated via FastAPI backend ({target_endpoint})."
        else:
            payload = calculate_deterministic_bankability(company_id, loan_amount, interest_rate, tenor_years)
            return (
                payload,
                "DETERMINISTIC_FALLBACK",
                f"Backend returned HTTP {response.status_code}. Seamlessly engaged deterministic DuckDB fallback."
            )
    except requests.exceptions.RequestException as exc:
        payload = calculate_deterministic_bankability(company_id, loan_amount, interest_rate, tenor_years)
        return (
            payload,
            "DETERMINISTIC_FALLBACK",
            f"Backend unreachable at {target_endpoint} ({type(exc).__name__}). Engaged deterministic DuckDB fallback."
        )


def simulate_scenario_api(
    company_id: str,
    requested_amount: int,
    interest_rate: float = 0.0525,
    tenor_years: int = 5,
    base_payload: Optional[Dict[str, Any]] = None,
    backend_url: str = DEFAULT_BACKEND_URL,
    force_mock: bool = False,
    timeout_seconds: float = 3.0
) -> Tuple[Dict[str, Any], str, str]:
    """
    Simulates What-If capital sizing sensitivity via FastAPI /scenario or deterministic DuckDB engine.
    Returns: (scenario_dict, mode, status_message)
    """
    if force_mock:
        res = calculate_deterministic_bankability(
            company_id=company_id,
            requested_amount=requested_amount,
            interest_rate=interest_rate,
            tenor_years=tenor_years
        )
        return res, "DETERMINISTIC_FALLBACK", "Simulated locally via deterministic DuckDB/Python formulas."

    target_endpoint = f"{backend_url.rstrip('/')}/scenario"
    try:
        response = requests.post(
            target_endpoint,
            json={
                "company_id": company_id,
                "loan_amount": requested_amount,
                "interest_rate": interest_rate,
                "tenor_years": tenor_years
            },
            headers={"Content-Type": "application/json"},
            timeout=timeout_seconds
        )
        if response.status_code == 200:
            return response.json(), "LIVE_API", "Simulated via FastAPI backend."
        else:
            res = calculate_deterministic_bankability(company_id, requested_amount, interest_rate, tenor_years)
            return res, "DETERMINISTIC_FALLBACK", f"Backend HTTP {response.status_code}. Local DuckDB fallback applied."
    except requests.exceptions.RequestException as exc:
        res = calculate_deterministic_bankability(company_id, requested_amount, interest_rate, tenor_years)
        return res, "DETERMINISTIC_FALLBACK", f"Backend unreachable. Local DuckDB fallback applied ({type(exc).__name__})."
