"""Uploaded CSVs must change stored financials and scores — never EcoTex defaults."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.duckdb_engine import (
    calculate_deterministic_bankability,
    parse_and_ingest_csv,
)


def _csv(rows: str) -> bytes:
    return rows.encode("utf-8")


FLAT_A = _csv(
    "fiscal_year;revenue;ebitda;net_income;total_assets;net_equity;total_debt;"
    "short_term_debt;cash_and_equivalents;capex\n"
    "2025;20000000;3800000;1700000;18000000;8500000;5200000;1300000;2500000;1100000\n"
)
FLAT_B = _csv(
    "fiscal_year;revenue;ebitda;net_income;total_assets;net_equity;total_debt;"
    "short_term_debt;cash_and_equivalents;capex\n"
    "2025;8000000;900000;300000;7000000;2500000;4100000;1400000;400000;500000\n"
)
SERIES = _csv(
    "Period,Data_value,Magnitude,Series_title_1,Series_title_2\n"
    "2025.06,1200,6,Sales (operating income),Total\n"
    "2025.06,900,6,Purchases and operating expenditure,Total\n"
    "2025.06,80,6,Salaries and wages paid,Total\n"
    "2024.06,100,6,Sales (operating income),Total\n"
)


def test_two_summary_csvs_produce_different_revenue():
    a = parse_and_ingest_csv(FLAT_A, "strong.csv", "ecotex")
    b = parse_and_ingest_csv(FLAT_B, "weak.csv", "ecotex")

    assert a["status"] == "SUCCESS"
    assert b["status"] == "SUCCESS"
    assert a["revenue"] == 20_000_000
    assert b["revenue"] == 8_000_000
    assert a["ebitda"] != b["ebitda"]
    assert a["rows_ingested"] == 1
    assert "14,200,000" not in a["message"]


def test_stats_style_series_uses_file_values_not_ecotex_defaults():
    result = parse_and_ingest_csv(SERIES, "business-financial-data.csv", "ecotex")

    assert result["status"] == "SUCCESS"
    assert result["rows_ingested"] == 4
    # 1200 * 10^6 from latest period Total sales
    assert result["revenue"] == 1_200_000_000
    assert result["revenue"] != 14_200_000


def test_ingested_file_changes_bankability_score():
    parse_and_ingest_csv(FLAT_A, "strong.csv", "ecotex")
    strong = calculate_deterministic_bankability("ecotex", 750_000)
    parse_and_ingest_csv(FLAT_B, "weak.csv", "ecotex")
    weak = calculate_deterministic_bankability("ecotex", 750_000)

    assert strong["revenue"] == 20_000_000
    assert weak["revenue"] == 8_000_000
    assert strong["financial_score"] != weak["financial_score"]


def test_unmapped_csv_does_not_silently_use_demo_figures():
    junk = _csv("foo,bar\nhello,world\n")
    result = parse_and_ingest_csv(junk, "notes.csv", "ecotex")

    assert result["status"] == "ERROR"
    assert result.get("revenue") is None
