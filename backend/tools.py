"""Agent tool functions backed by DuckDB."""

from typing import Any

from analytics.financial import compute_ratios
from backend.config import settings
from ingestion.loaders import get_connection
from rag.retrieval import search_documents as bm25_search


def _row_to_dict(columns: list[str], row: tuple) -> dict[str, Any]:
    return dict(zip(columns, row, strict=False))


def get_company_financials(company_name: str) -> dict[str, Any]:
    conn = get_connection(settings.duckdb_path)
    try:
        row = conn.execute(
            """
            SELECT company_id, company_name, province, sector, revenue, ebitda, cash,
                   short_term_debt, long_term_debt, interest_expense, employees, revenue_growth
            FROM company_financials
            WHERE company_name ILIKE ?
            LIMIT 1
            """,
            [f"%{company_name}%"],
        ).fetchone()
        if not row:
            return {"error": f"Company not found: {company_name}"}

        cols = [
            "company_id", "company_name", "province", "sector", "revenue", "ebitda", "cash",
            "short_term_debt", "long_term_debt", "interest_expense", "employees", "revenue_growth",
        ]
        data = _row_to_dict(cols, row)
        data["ratios"] = compute_ratios(data)
        return data
    finally:
        conn.close()


def get_regional_risk(province: str) -> dict[str, Any]:
    conn = get_connection(settings.duckdb_path)
    try:
        row = conn.execute(
            """
            SELECT province, year, liquidity_indicator, avg_interest_rate, loan_default_rate
            FROM regional_risk
            WHERE province ILIKE ?
            ORDER BY year DESC
            LIMIT 1
            """,
            [f"%{province}%"],
        ).fetchone()
        if not row:
            return {"error": f"No regional data for: {province}"}
        cols = ["province", "year", "liquidity_indicator", "avg_interest_rate", "loan_default_rate"]
        return _row_to_dict(cols, row)
    finally:
        conn.close()


def get_sector_performance(province: str, sector: str) -> dict[str, Any]:
    conn = get_connection(settings.duckdb_path)
    try:
        row = conn.execute(
            """
            SELECT province, sector_name, year, aggregate_turnover,
                   active_enterprises, economic_performance_index
            FROM sector_performance
            WHERE province ILIKE ? AND sector_name ILIKE ?
            ORDER BY year DESC
            LIMIT 1
            """,
            [f"%{province}%", f"%{sector}%"],
        ).fetchone()
        if not row:
            row = conn.execute(
                """
                SELECT province, sector_name, year, aggregate_turnover,
                       active_enterprises, economic_performance_index
                FROM sector_performance
                WHERE province ILIKE ?
                ORDER BY year DESC
                LIMIT 1
                """,
                [f"%{province}%"],
            ).fetchone()
        if not row:
            return {"error": f"No sector data for {sector} in {province}"}
        cols = [
            "province", "sector_name", "year", "aggregate_turnover",
            "active_enterprises", "economic_performance_index",
        ]
        return _row_to_dict(cols, row)
    finally:
        conn.close()


def search_documents(query: str, company_name: str | None = None) -> list[dict[str, Any]]:
    return bm25_search(query, company_name=company_name, top_k=3)
