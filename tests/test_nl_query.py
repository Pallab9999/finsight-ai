"""Safety guard on LLM-generated SQL.

The model writes this SQL, so these tests pin the boundary between what is
allowed to reach DuckDB and what is not.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.nl_query import MAX_ROWS, UnsafeQuery, guard_sql, run_nl_query, schema_snapshot
from ingestion.loaders import seed_database


@pytest.fixture(scope="module", autouse=True)
def seeded():
    seed_database(ROOT / "data" / "finsight.duckdb")


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM company_financials",
        "DROP TABLE documents",
        "UPDATE company_financials SET revenue = 0",
        "INSERT INTO documents VALUES (1)",
        "ALTER TABLE documents ADD COLUMN x INT",
        "ATTACH 'evil.db' AS evil",
        "COPY documents TO 'out.csv'",
        "PRAGMA database_list",
        "INSTALL httpfs",
        "CREATE TABLE t AS SELECT 1",
    ],
)
def test_guard_rejects_write_and_admin_statements(sql):
    with pytest.raises(UnsafeQuery):
        guard_sql(sql)


def test_guard_rejects_stacked_statements():
    with pytest.raises(UnsafeQuery, match="Multiple SQL statements"):
        guard_sql("SELECT 1; DROP TABLE documents")


def test_guard_rejects_write_hidden_after_select():
    with pytest.raises(UnsafeQuery):
        guard_sql("SELECT * FROM documents WHERE 1=1 UNION SELECT 1; DELETE FROM documents")


def test_guard_rejects_empty():
    with pytest.raises(UnsafeQuery):
        guard_sql("   ")


def test_guard_allows_select_and_enforces_limit():
    safe = guard_sql("SELECT company_name FROM company_financials")

    assert safe.endswith(f"LIMIT {MAX_ROWS}")


def test_guard_preserves_existing_limit():
    safe = guard_sql("SELECT company_name FROM company_financials LIMIT 5")

    assert safe.count("LIMIT") == 1
    assert safe.endswith("LIMIT 5")


def test_guard_allows_cte_and_strips_fences():
    safe = guard_sql("```sql\nWITH t AS (SELECT 1 AS a) SELECT a FROM t\n```")

    assert safe.startswith("WITH")
    assert "```" not in safe


def test_guard_does_not_flag_column_names_containing_keywords():
    """`created_at` contains 'create'; word boundaries must prevent a false reject."""
    safe = guard_sql("SELECT company_id FROM documents WHERE metadata IS NOT NULL")

    assert safe.startswith("SELECT")


def test_schema_snapshot_lists_real_tables():
    schema = schema_snapshot()

    for table in ("company_financials", "documents", "regional_risk", "sector_performance"):
        assert table in schema


def test_run_nl_query_needs_a_question():
    result = run_nl_query("  ")

    assert result["error"] == "Ask a question first."


def test_run_nl_query_reports_missing_key_instead_of_guessing(monkeypatch):
    """Without a key this feature must say so, not fabricate an answer."""
    monkeypatch.setattr("analytics.nl_query.gemini_key", lambda: "")

    result = run_nl_query("What is EcoTex revenue?")

    assert result["rows"] == []
    assert "GEMINI_API_KEY" in result["error"]


def test_run_nl_query_surfaces_guard_rejection(monkeypatch):
    monkeypatch.setattr(
        "analytics.nl_query.generate_sql",
        lambda q: ("DELETE FROM documents", "stubbed"),
    )

    result = run_nl_query("wipe the documents")

    assert "safety guard" in result["error"]
    assert result["rows"] == []


def test_run_nl_query_executes_generated_select(monkeypatch):
    monkeypatch.setattr(
        "analytics.nl_query.generate_sql",
        lambda q: ("SELECT company_name, revenue FROM company_financials", "stubbed"),
    )

    result = run_nl_query("list companies and revenue")

    assert result["error"] is None
    assert result["columns"] == ["company_name", "revenue"]
    assert result["row_count"] >= 1
    assert "EcoTex Milano" in [row[0] for row in result["rows"]]
