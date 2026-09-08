"""Natural-language analytics over DuckDB (text-to-SQL).

An LLM writes the SQL, so correctness cannot be assumed. Three independent
guards contain that:

1.  The real schema is read from DuckDB and injected into the prompt, so the
    model sees actual column names instead of guessing them.
2.  `guard_sql` rejects anything that is not a single read-only SELECT/WITH, and
    enforces a row limit.
3.  Execution prefers a read_only DuckDB connection, which makes writes fail at
    the engine level even if the guard were bypassed.

Unlike the scoring pipeline this feature genuinely requires a key for SQL generation.
If SQL cannot be built, the same LLM still answers from a compact DuckDB snapshot.
"""

from __future__ import annotations

import logging
import re

import duckdb

from backend.config import export_dotenv_secrets, gemini_key, settings
from backend.llm import bedrock_available, bedrock_api_key_format_ok, complete_text
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


def heuristic_sql(question: str) -> str:
    """Deterministic read-only SQL so questions still resolve without an LLM."""
    q = (question or "").lower()
    if any(token in q for token in ("default", "npl", "sofferenze")):
        return (
            "SELECT province, year, loan_default_rate, avg_interest_rate, "
            "liquidity_indicator FROM regional_risk "
            "ORDER BY loan_default_rate DESC LIMIT 25"
        )
    if any(token in q for token in ("sector", "turnover", "ateco")):
        return (
            "SELECT province, sector_name, year, aggregate_turnover, "
            "active_enterprises FROM sector_performance LIMIT 25"
        )
    if "esg" in q:
        return (
            "SELECT company_name, sector, environmental_indicator, "
            "social_indicator, governance_indicator FROM esg_data LIMIT 25"
        )
    return (
        "SELECT company_name, province, sector, revenue, ebitda, employees, "
        "cash, short_term_debt FROM company_financials LIMIT 25"
    )


def lakehouse_sql(question: str) -> str:
    q = (question or "").lower()
    if any(token in q for token in ("default", "npl", "sofferenze")):
        return (
            "SELECT province, region, default_rate_npl, benchmark_spread "
            "FROM bdi_provincial_credit LIMIT 25"
        )
    if any(token in q for token in ("sector", "turnover", "ateco")):
        return (
            "SELECT sector_name, ateco_division, turnover_growth_yoy, outlook "
            "FROM lombardia_sectors LIMIT 25"
        )
    return (
        "SELECT c.company_name, c.province, c.sector, f.fiscal_year, f.revenue, "
        "f.ebitda, f.net_income FROM financial_statements f "
        "JOIN companies c ON c.company_id = f.company_id "
        "ORDER BY f.ingested_at DESC LIMIT 25"
    )


def _fmt_value(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        if abs(value) >= 1000:
            return f"€{value:,.0f}"
        return f"{value:.2f}"
    if isinstance(value, int) and abs(value) >= 10000:
        return f"€{value:,}"
    return str(value)


def _prose_from_rows(question: str, columns: list, rows: list) -> str:
    if not rows:
        return ""
    lines = [f'Results for "{question.strip()}":']
    for row in rows[:8]:
        parts = [f"{col} {_fmt_value(val)}" for col, val in zip(columns, row)]
        lines.append("- " + " · ".join(parts))
    extra = len(rows) - 8
    if extra > 0:
        lines.append(f"... and {extra} more row(s).")
    return "\n\n".join(lines)


def generate_sql(question: str) -> tuple[str | None, str]:
    """Ask Bedrock (then Gemini) for SQL. Returns (sql, status)."""
    export_dotenv_secrets()
    can_llm = bool(gemini_key()) or (
        bedrock_available() and bedrock_api_key_format_ok()
    )
    if not can_llm:
        return None, "no-llm"

    prompt = PROMPT_TEMPLATE.format(
        schema=schema_snapshot(), question=question.strip(), max_rows=MAX_ROWS
    )
    raw, provider = complete_text(prompt, max_tokens=400, temperature=0.0)
    if not raw:
        return None, f"SQL generation failed via {provider}."
    if "unanswerable" in raw.lower()[:40]:
        return None, "That question cannot be answered from the available tables."
    return _strip_fences(raw), f"SQL generated by {provider}."


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


def _connect_lakehouse() -> tuple:
    from app.duckdb_engine import get_connection as lake_connection

    return lake_connection(), False


def _fill_from_sql(result: dict, sql: str, status: str, connector=_connect_read_only) -> bool:
    """Execute guarded SQL. Returns True when at least one row was produced."""
    try:
        safe_sql = guard_sql(sql)
    except UnsafeQuery as exc:
        result["sql"] = sql
        result["error"] = f"Query rejected by the safety guard: {exc}"
        return False

    result["sql"] = safe_sql
    result["status"] = status
    conn = None
    try:
        conn, read_only = connector()
        result["read_only"] = read_only
        cursor = conn.execute(safe_sql)
        rows = cursor.fetchall()
        result["columns"] = [d[0] for d in cursor.description] if cursor.description else []
        result["rows"] = [list(r) for r in rows]
        result["row_count"] = len(rows)
        result["error"] = None
        if rows:
            result["answer"] = _prose_from_rows(
                result["question"], result["columns"], result["rows"]
            )
            return True
        result["status"] = "Query ran successfully but matched no rows."
        return False
    except Exception as exc:
        logger.warning("NL query execution failed: %s", exc)
        result["error"] = f"SQL failed to execute ({type(exc).__name__}): {exc}"
        return False
    finally:
        if conn is not None and connector is _connect_read_only:
            conn.close()


def run_nl_query(question: str) -> dict:
    """Answer an analytics question from DuckDB.

    Tries an LLM SQL draft when a usable key exists, then a deterministic
    query so the console still returns a result without Bedrock/Gemini.
    """
    result: dict = {
        "question": question,
        "sql": None,
        "columns": [],
        "rows": [],
        "row_count": 0,
        "read_only": False,
        "status": "",
        "answer": None,
        "error": None,
    }

    if not question or not question.strip():
        result["error"] = "Ask a question first."
        return result

    sql, status = generate_sql(question)
    if sql:
        if _fill_from_sql(result, sql, status):
            return result
        if "safety guard" in (result.get("error") or ""):
            return result

    hsql = heuristic_sql(question)
    if hsql and _fill_from_sql(result, hsql, "Answered from DuckDB."):
        return result

    try:
        lsql = lakehouse_sql(question)
        if lsql and _fill_from_sql(
            result,
            lsql,
            "Answered from the live lakehouse.",
            connector=_connect_lakehouse,
        ):
            return result
    except Exception as exc:
        logger.info("Lakehouse query skipped: %s", exc)

    answer, provider = answer_from_snapshot(question, sql_error=result.get("error"))
    if answer:
        result["answer"] = answer
        result["error"] = None
        result["status"] = f"Answered from live credit data via {provider}."
    elif not result["error"]:
        result["error"] = status or "No matching credit data."
    return result


ANSWER_PROMPT = """You are FinSight AI, a credit-analytics assistant for Italian SMEs and bank underwriters.

LIVE DATA SNAPSHOT (authoritative — do not invent figures):
{brief}

QUESTION:
{question}

{sql_note}

Write a direct answer in 1-3 short paragraphs. Use euro amounts, ratios, and place names from the snapshot. If the snapshot does not contain the answer, say what is missing and what is available. Do not mention SQL, Bedrock, Gemini, or internal tools."""


def _table_csv(conn, table: str, limit: int = 12) -> str | None:
    try:
        df = conn.execute(f"SELECT * FROM {table} LIMIT {limit}").fetchdf()
    except Exception:
        return None
    if df is None or df.empty:
        return None
    return f"{table}\n{df.to_csv(index=False)}"


def _data_brief() -> str:
    """Compact snapshot from the Streamlit lakehouse and the analytics DuckDB."""
    chunks: list[str] = []

    try:
        from app.duckdb_engine import get_connection as lake_connection

        lake = lake_connection()
        for table in (
            "companies",
            "financial_statements",
            "bdi_provincial_credit",
            "lombardia_sectors",
        ):
            if csv := _table_csv(lake, table):
                chunks.append(csv)
    except Exception as exc:
        logger.info("Lakehouse snapshot skipped: %s", exc)

    try:
        conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
        try:
            for table in (
                "company_financials",
                "regional_risk",
                "sector_performance",
                "esg_data",
            ):
                if csv := _table_csv(conn, table):
                    chunks.append(csv)
        finally:
            conn.close()
    except Exception as exc:
        logger.info("Analytics snapshot skipped: %s", exc)

    return "\n\n".join(chunks)[:14000]


def answer_from_snapshot(question: str, sql_error: str | None = None) -> tuple[str | None, str]:
    """Answer from a DuckDB snapshot when SQL is unavailable or failed."""
    export_dotenv_secrets()
    brief = _data_brief()
    if not brief.strip():
        return None, "none"

    sql_note = ""
    if sql_error:
        sql_note = (
            f"A structured query could not be used ({sql_error}). "
            "Answer from the snapshot only."
        )

    prompt = ANSWER_PROMPT.format(
        brief=brief, question=question.strip(), sql_note=sql_note
    )
    text, provider = complete_text(prompt, max_tokens=700, temperature=0.2)
    if text:
        return text, provider
    return (
        "The language model was unreachable. Here is the live credit data:\n\n"
        + brief[:3500],
        "snapshot",
    )
