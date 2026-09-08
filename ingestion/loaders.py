"""Load data from bankbench-data-sync SQLite and seed DuckDB."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import duckdb

from ingestion.cleaner import standardize_province, standardize_sector
from ingestion.normalizer import normalize_lombardia_record

ECOTEX_FINANCIALS = {
    "company_id": "ecotex-001",
    "company_name": "EcoTex Milano",
    "province": "Milano",
    "sector": "Textile Manufacturing",
    "revenue": 4_200_000.0,
    "ebitda": 630_000.0,
    "cash": 520_000.0,
    "short_term_debt": 380_000.0,
    "long_term_debt": 1_100_000.0,
    "interest_expense": 85_000.0,
    "employees": 85,
    "revenue_growth": 0.082,
}

ECOTEX_ESG = {
    "company_id": "ecotex-001",
    "company_name": "EcoTex Milano",
    "sector": "Textile Manufacturing",
    "environmental_indicator": 0.82,
    "social_indicator": 0.75,
    "governance_indicator": 0.78,
    "carbon_exposure": 0.35,
    "evidence_quality": 0.88,
    "esg_evidence_source": "EcoTex Sustainability Report 2025",
}

SYNTHETIC_REGIONAL = [
    {
        "province": "Milano",
        "year": 2024,
        "liquidity_indicator": 0.78,
        "avg_interest_rate": 0.045,
        "loan_default_rate": 0.018,
    },
    {
        "province": "Bergamo",
        "year": 2024,
        "liquidity_indicator": 0.72,
        "avg_interest_rate": 0.048,
        "loan_default_rate": 0.022,
    },
]

SYNTHETIC_SECTOR = [
    {
        "province": "Milano",
        "sector_name": "Textile Manufacturing",
        "year": 2024,
        "aggregate_turnover": 2_800_000_000.0,
        "active_enterprises": 1240,
        "economic_performance_index": 1.06,
    },
    {
        "province": "Milano",
        "sector_name": "Manufacturing",
        "year": 2024,
        "aggregate_turnover": 45_000_000_000.0,
        "active_enterprises": 18500,
        "economic_performance_index": 1.03,
    },
]

ESG_DOCUMENT_CHUNKS = [
    {
        "document_id": "esg-001",
        "company_id": "ecotex-001",
        "source_name": "EcoTex Sustainability Report 2025",
        "document_type": "sustainability_report",
        "chunk_id": "chunk-1",
        "text_content": (
            "EcoTex Milano has committed to a 40% reduction in water consumption by 2027 "
            "through the installation of advanced water-recycling equipment. The proposed "
            "€750,000 financing aligns with EU Taxonomy environmental objectives for "
            "sustainable manufacturing."
        ),
        "metadata": json.dumps({"page": 12, "section": "Environmental Goals"}),
    },
    {
        "document_id": "esg-001",
        "company_id": "ecotex-001",
        "source_name": "EcoTex Sustainability Report 2025",
        "document_type": "sustainability_report",
        "chunk_id": "chunk-2",
        "text_content": (
            "The company maintains ISO 14001 certification and reports a 15% reduction "
            "in carbon intensity over the past three years. Employee safety metrics exceed "
            "industry benchmarks with zero lost-time incidents in 2024."
        ),
        "metadata": json.dumps({"page": 18, "section": "Certifications"}),
    },
    {
        "document_id": "policy-001",
        "company_id": "ecotex-001",
        "source_name": "Banca d'Italia Regional Credit Bulletin",
        "document_type": "policy",
        "chunk_id": "chunk-1",
        "text_content": (
            "Regional credit conditions in Lombardia remain supportive for SME lending, "
            "with stable liquidity indicators and moderate default rates. Manufacturing "
            "sector credit demand shows positive momentum in the Milano province."
        ),
        "metadata": json.dumps({"source": "Banca d'Italia", "year": 2024}),
    },
]


def load_bankbench_records(sqlite_path: Path) -> list[dict[str, Any]]:
    if not sqlite_path.exists():
        return []
    conn = sqlite3.connect(sqlite_path)
    try:
        rows = conn.execute("SELECT payload FROM raw_records").fetchall()
        records = []
        for (payload,) in rows:
            try:
                records.append(json.loads(payload))
            except json.JSONDecodeError:
                continue
        return records
    finally:
        conn.close()


def create_duckdb_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS company_financials (
            company_id VARCHAR,
            company_name VARCHAR,
            province VARCHAR,
            sector VARCHAR,
            revenue DOUBLE,
            ebitda DOUBLE,
            cash DOUBLE,
            short_term_debt DOUBLE,
            long_term_debt DOUBLE,
            interest_expense DOUBLE,
            employees INTEGER,
            revenue_growth DOUBLE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS regional_risk (
            province VARCHAR,
            year INTEGER,
            liquidity_indicator DOUBLE,
            avg_interest_rate DOUBLE,
            loan_default_rate DOUBLE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sector_performance (
            province VARCHAR,
            sector_name VARCHAR,
            year INTEGER,
            aggregate_turnover DOUBLE,
            active_enterprises INTEGER,
            economic_performance_index DOUBLE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS esg_data (
            company_id VARCHAR,
            company_name VARCHAR,
            sector VARCHAR,
            environmental_indicator DOUBLE,
            social_indicator DOUBLE,
            governance_indicator DOUBLE,
            carbon_exposure DOUBLE,
            evidence_quality DOUBLE,
            esg_evidence_source VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            document_id VARCHAR,
            company_id VARCHAR,
            source_name VARCHAR,
            document_type VARCHAR,
            chunk_id VARCHAR,
            text_content VARCHAR,
            metadata VARCHAR
        )
    """)


def seed_database(
    duckdb_path: Path,
    bankbench_sqlite_path: Path | None = None,
) -> None:
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(duckdb_path))
    try:
        create_duckdb_schema(conn)
        conn.execute("DELETE FROM company_financials")
        conn.execute("DELETE FROM regional_risk")
        conn.execute("DELETE FROM sector_performance")
        conn.execute("DELETE FROM esg_data")
        conn.execute("DELETE FROM documents")

        conn.execute(
            "INSERT INTO company_financials VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            list(ECOTEX_FINANCIALS.values()),
        )

        for row in SYNTHETIC_REGIONAL:
            conn.execute(
                "INSERT INTO regional_risk VALUES (?, ?, ?, ?, ?)",
                list(row.values()),
            )

        sector_rows = list(SYNTHETIC_SECTOR)
        if bankbench_sqlite_path:
            lombardia = load_bankbench_records(bankbench_sqlite_path)
            for record in lombardia:
                normalized = normalize_lombardia_record(record)
                if normalized:
                    sector_rows.append(normalized)

        seen = set()
        for row in sector_rows:
            key = (row["province"], row["sector_name"], row["year"])
            if key in seen:
                continue
            seen.add(key)
            conn.execute(
                "INSERT INTO sector_performance VALUES (?, ?, ?, ?, ?, ?)",
                [
                    row["province"],
                    row["sector_name"],
                    row["year"],
                    row["aggregate_turnover"],
                    row["active_enterprises"],
                    row["economic_performance_index"],
                ],
            )

        conn.execute(
            "INSERT INTO esg_data VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            list(ECOTEX_ESG.values()),
        )

        for doc in ESG_DOCUMENT_CHUNKS:
            conn.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?)",
                list(doc.values()),
            )
    finally:
        conn.close()


def get_connection(duckdb_path: Path) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(duckdb_path))
