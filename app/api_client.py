"""
FinSight AI - Backend Integration Client
Calls FinSight FastAPI POST /evaluate with automatic deterministic fallback.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.mock_data import calculate_scenario, get_base_demo_payload

DEFAULT_BACKEND_URL = "http://localhost:8000"


def _enrich_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure UI-expected keys exist on live API responses."""
    if "scenario" not in data or not isinstance(data["scenario"], dict):
        data["scenario"] = calculate_scenario(data, 1_000_000)
    else:
        scenario = data["scenario"]
        if "dscr" not in scenario:
            enriched = calculate_scenario(data, int(scenario.get("loan_amount", 1_000_000)))
            scenario.setdefault("dscr", enriched.get("dscr"))
            scenario.setdefault("summary", enriched.get("summary"))
            scenario.setdefault("confidence", enriched.get("confidence"))

    for item in data.get("evidence", []):
        if "category" not in item:
            source = str(item.get("source", "")).lower()
            if "scoring" in source or "deterministic" in source:
                item["category"] = "CALCULATION"
            elif "synthesis" in source or "reason" in source:
                item["category"] = "REASONING"
            else:
                item["category"] = "FACT"
    return data


def evaluate_application(
    query: str,
    loan_amount: int = 750_000,
    backend_url: str = DEFAULT_BACKEND_URL,
    force_mock: bool = False,
    timeout_seconds: float = 30.0,
    scenario_loan_amount: int | None = None,
) -> tuple[dict[str, Any], str, str]:
    """
    Returns (payload, mode, status_message).
    mode is LIVE_API or DETERMINISTIC_FALLBACK.
    """
    if force_mock:
        payload = get_base_demo_payload()
        if scenario_loan_amount:
            payload["scenario"] = calculate_scenario(payload, scenario_loan_amount)
        elif loan_amount != 750_000:
            payload["scenario"] = calculate_scenario(payload, loan_amount)
        return payload, "DETERMINISTIC_FALLBACK", "Operating in safe deterministic fallback mode."

    target_endpoint = f"{backend_url.rstrip('/')}/evaluate"
    request_data: dict[str, Any] = {"query": query}
    if scenario_loan_amount:
        request_data["scenario_loan_amount"] = scenario_loan_amount

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(target_endpoint, json=request_data)
        if response.status_code == 200:
            data = _enrich_payload(response.json())
            return data, "LIVE_API", f"Successfully evaluated via FastAPI ({target_endpoint})."
        fallback = get_base_demo_payload()
        return (
            fallback,
            "DETERMINISTIC_FALLBACK",
            f"Backend returned HTTP {response.status_code}. Using deterministic fallback.",
        )
    except httpx.RequestError as exc:
        fallback = get_base_demo_payload()
        return (
            fallback,
            "DETERMINISTIC_FALLBACK",
            f"Backend unreachable at {target_endpoint} ({type(exc).__name__}). Using fallback.",
        )
