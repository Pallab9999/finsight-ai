"""Map raw Lombardia records to FinSight schema fields."""

from typing import Any

from ingestion.cleaner import standardize_province, standardize_sector


def normalize_lombardia_record(record: dict[str, Any]) -> dict[str, Any] | None:
    """Best-effort mapping from Socrata JSON to sector_performance row."""
    province = standardize_province(
        str(record.get("comune") or record.get("provincia") or record.get("Comune") or "Milano")
    )
    sector = standardize_sector(
        str(record.get("settore") or record.get("tipologia") or record.get("Settore") or "Manufacturing")
    )

    turnover = _first_float(record, ["fatturato", "turnover", "valore", "aggregate_turnover"])
    enterprises = _first_int(record, ["imprese", "numero_imprese", "active_enterprises", "n_imprese"])
    if turnover is None and enterprises is None:
        return None

    return {
        "province": province,
        "sector_name": sector,
        "year": int(record.get("anno") or record.get("year") or 2024),
        "aggregate_turnover": turnover or 0.0,
        "active_enterprises": enterprises or 0,
        "economic_performance_index": 1.02 if turnover and turnover > 0 else 1.0,
    }


def _first_float(record: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        if key in record and record[key] is not None:
            try:
                return float(record[key])
            except (TypeError, ValueError):
                continue
    return None


def _first_int(record: dict[str, Any], keys: list[str]) -> int | None:
    for key in keys:
        if key in record and record[key] is not None:
            try:
                return int(float(record[key]))
            except (TypeError, ValueError):
                continue
    return None
