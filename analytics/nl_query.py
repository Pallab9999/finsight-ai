"""Natural-language analytics over DuckDB (text-to-SQL).

An LLM writes the SQL, so correctness cannot be assumed. Three independent
guards contain that:

1.  The real schema is read from DuckDB and injected into the prompt, so the
    model sees actual column names instead of guessing them.
2.  `guard_sql` rejects anything that is not a single read-only SELECT/WITH, and
    enforces a row limit.
3.  Execution prefers a read_only DuckDB connection, which makes writes fail at
    the engine level even if the guard were bypassed.

Unlike the scoring pipeline this feature genuinely requires a key; without one it
reports that instead of degrading, because a wrong answer is worse than no answer.
"""

from __future__ import annotations

import logging
import re

import duckdb

from backend.config import settings
from ingestion.loaders import create_duckdb_schema, get_connection

logger = logging.getLogger(__name__)

MAX_ROWS = 200

# Matched with word boundaries so column names like `created_at` are not caught.
FORBIDDEN_KEYWORDS = (
    "insert", "update", "delete", "drop", "create", "alter", "truncate",
    "attach", "detach", "copy", "install", "load", "pragma", "set",
    "export", "import", "replace", "grant", "revoke", "vacuum", "call",
)

PROMPT_TEMPLATE = """You are a SQL analyst for FinSight AI, writing DuckDB SQL over a \
credit-analytics database.

DATABASE SCHEMA (authoritative - use only these tables and columns):
{schema}

QUESTION:
{question}

Rules:
- Return a single read-only SELECT statement (a leading WITH clause is allowed).
- Use only tables and columns from the schema above. Never invent names.
- DuckDB dialect. Use ILIKE for case-insensitive text matching.
- Always include a LIMIT of at most {max_rows}.
- Prefer readable column aliases, and round monetary or ratio values sensibly.
- If the question cannot be answered from this schema, return exactly: UNANSWERABLE

Return only the SQL, with no explanation and no markdown fences."""


class UnsafeQuery(Exception):
    """Raised when generated SQL is not a safe read-only query."""


def schema_snapshot() -> str:
    """Read the live schema so the prompt cannot drift from the database."""
    conn = get_connection(settings.duckdb_path)
    try:
        create_duckdb_schema(conn)
        rows = conn.execute(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'main'
            ORDER BY table_name, ordinal_position
            """
        ).fetchall()
    finally:
        conn.close()

    tables: dict[str, list[str]] = {}
    for table, column, dtype in rows:
        tables.setdefault(table, []).append(f"{column} {dtype}")

    return "\n".join(
        f"- {table}({', '.join(columns)})" for table, columns in sorted(tables.items())
    )


def _strip_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:sql)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def guard_sql(sql: str, max_rows: int = MAX_ROWS) -> str:
    """Validate generated SQL and return an execution-safe version.

    Raises UnsafeQuery when the statement is not a single read-only query.
    """
    cleaned = _strip_fences(sql).rstrip(";").strip()
    if not cleaned:
        raise UnsafeQuery("The model returned an empty query.")

    # Reject stacked statements. The trailing semicolon is already removed, so
    # any remaining one separates a second statement.
    if ";" in cleaned:
        raise UnsafeQuery("Multiple SQL statements are not allowed.")

    if not re.match(r"^\s*(select|with)\b", cleaned, re.I):
        raise UnsafeQuery("Only SELECT queries are allowed.")

    lowered = cleaned.lower()
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            raise UnsafeQuery(f"Query contains the forbidden keyword '{keyword}'.")

    if not re.search(r"\blimit\b", lowered):
        cleaned = f"{cleaned} LIMIT {max_rows}"

    return cleaned


def generate_sql(question: str) -> tuple[str | None, str]:
    """Ask Gemini for SQL. Returns (sql, status)."""
    if not settings.gemini_api_key:
        return None, (
            "Natural-language analytics needs a Gemini API key. Set GEMINI_API_KEY "
            "in .env (or in Streamlit secrets when hosted), then reload."
        )

    prompt = PROMPT_TEMPLATE.format(
        schema=schema_snapshot(), question=question.strip(), max_rows=MAX_ROWS
    )

    try:
        from google import genai

        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config={"temperature": 0.0},
        )
        raw = (response.text or "").strip()
    except Exception as exc:
        logger.warning("SQL generation failed: %s", exc)
        return None, f"SQL generation failed ({type(exc).__name__})."

    if not raw:
        return None, "The model returned no SQL."
    if "unanswerable" in raw.lower()[:40]:
        return None, "That question cannot be answered from the available tables."

    return _strip_fences(raw), "SQL generated by Gemini."


def _connect_read_only() -> tuple[duckdb.DuckDBPyConnection, bool]:
    """Prefer a read-only connection; fall back if the file is held for writing.

    The guard still applies in the fallback case, so this degrades the depth of
    defence rather than removing it.
    """
    try:
        return duckdb.connect(str(settings.duckdb_path), read_only=True), True
    except Exception as exc:
        logger.info("Read-only connection unavailable, using standard: %s", exc)
        return get_connection(settings.duckdb_path), False


def run_nl_query(question: str) -> dict:
    """Answer an analytics question with SQL.

    Returns a dict with: question, sql, columns, rows, row_count, read_only,
    status, and error (None on success).
    """
    result: dict = {
        "question": question,
        "sql": None,
        "columns": [],
        "rows": [],
        "row_count": 0,
        "read_only": False,
        "status": "",
        "error": None,
    }

    if not question or not question.strip():
        result["error"] = "Ask a question first."
        return result

    sql, status = generate_sql(question)
    result["status"] = status
    if not sql:
        result["error"] = status
        return result

    try:
        safe_sql = guard_sql(sql)
    except UnsafeQuery as exc:
        result["sql"] = sql
        result["error"] = f"Query rejected by the safety guard: {exc}"
        return result

    result["sql"] = safe_sql

    conn, read_only = _connect_read_only()
    result["read_only"] = read_only
    try:
        cursor = conn.execute(safe_sql)
        rows = cursor.fetchall()
        result["columns"] = [d[0] for d in cursor.description] if cursor.description else []
        result["rows"] = [list(r) for r in rows]
        result["row_count"] = len(rows)
        if not rows:
            result["status"] = "Query ran successfully but matched no rows."
    except Exception as exc:
        logger.warning("NL query execution failed: %s", exc)
        result["error"] = f"SQL failed to execute ({type(exc).__name__}): {exc}"
    finally:
        conn.close()

    return result
