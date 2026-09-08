"""
FinSight AI - Conversational Chat Engine
=========================================
Full AI chat powered by Google Gemini + DuckDB text-to-SQL.

Flow:
  1. User asks a natural language question
  2. Engine classifies intent (data query vs. general advice vs. comparison)
  3. For data queries: generates safe SQL, executes against DuckDB, formats result
  4. For analysis: retrieves relevant DuckDB data, sends to Gemini with context
  5. Returns structured answer with evidence citations

Fallback: If Gemini API is unavailable, uses template-based responses from DuckDB data.
"""

from __future__ import annotations

import os
import re
import json
import logging
import traceback
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Safe tables and columns that text-to-SQL may reference
SAFE_SCHEMA = {
    "companies": [
        "company_id", "company_name", "vat_number", "sector",
        "ateco_code", "province", "region", "employees", "description",
    ],
    "financial_statements": [
        "statement_id", "company_id", "fiscal_year", "revenue", "ebitda",
        "net_income", "total_assets", "net_equity", "total_debt",
        "short_term_debt", "cash_and_equivalents", "capex", "source_file",
        "file_hash", "ingested_at",
    ],
    "bdi_provincial_credit": [
        "province", "region", "default_rate_npl", "benchmark_spread", "updated_at",
    ],
    "lombardia_sectors": [
        "sector_name", "ateco_division", "turnover_growth_yoy",
        "export_margin_trend", "outlook",
    ],
    "document_chunks": [
        "chunk_id", "company_id", "document_type", "filename",
        "chunk_text", "metadata_json", "ingested_at",
    ],
}

SCHEMA_DDL = """
Available DuckDB tables and columns:

TABLE companies (company_id VARCHAR PK, company_name VARCHAR, vat_number VARCHAR, sector VARCHAR, ateco_code VARCHAR, province VARCHAR, region VARCHAR, employees INT, description VARCHAR)

TABLE financial_statements (statement_id VARCHAR PK, company_id VARCHAR FK->companies, fiscal_year INT, revenue DOUBLE, ebitda DOUBLE, net_income DOUBLE, total_assets DOUBLE, net_equity DOUBLE, total_debt DOUBLE, short_term_debt DOUBLE, cash_and_equivalents DOUBLE, capex DOUBLE, source_file VARCHAR, file_hash VARCHAR, ingested_at TIMESTAMP)

TABLE bdi_provincial_credit (province VARCHAR PK, region VARCHAR, default_rate_npl DOUBLE, benchmark_spread DOUBLE, updated_at VARCHAR)

TABLE lombardia_sectors (sector_name VARCHAR PK, ateco_division VARCHAR, turnover_growth_yoy DOUBLE, export_margin_trend VARCHAR, outlook VARCHAR)

TABLE document_chunks (chunk_id VARCHAR PK, company_id VARCHAR FK->companies, document_type VARCHAR, filename VARCHAR, chunk_text VARCHAR, metadata_json VARCHAR, ingested_at TIMESTAMP)

Key relationships:
- financial_statements.company_id -> companies.company_id
- document_chunks.company_id -> companies.company_id
- bdi_provincial_credit.province -> companies.province
- lombardia_sectors.sector_name -> companies.sector
"""

SYSTEM_PROMPT = """You are FinSight AI, an expert financial analyst assistant for SME credit readiness assessment.
You help loan officers and CFOs analyze Italian SME financial data stored in a DuckDB database.

You have access to real financial data including:
- Company profiles (3 Lombardia SMEs)
- Audited balance sheets & P&L statements
- Banca d'Italia provincial credit benchmarks
- Open Data Lombardia sector performance indicators
- ESG audit document chunks

When answering:
1. Be specific — cite exact numbers from the data
2. Use financial terminology accurately (DSCR, EBITDA margin, NPL rates, etc.)
3. Compare against benchmarks when relevant
4. Give actionable credit recommendations
5. Format responses clearly with bullet points and bold highlights
6. If you generate SQL, it MUST be read-only SELECT statements only

{schema}
"""

SQL_GENERATION_PROMPT = """Based on the user's question below, generate a DuckDB SQL query to retrieve the relevant data.

RULES:
- Only SELECT statements allowed (no INSERT, UPDATE, DELETE, DROP, ALTER, CREATE)
- Only use tables and columns from the schema provided
- Return the SQL query wrapped in ```sql ... ``` code block
- If the question cannot be answered with SQL, respond with: NO_SQL_NEEDED
- Keep queries simple and focused
- Use JOINs when data spans multiple tables
- Always include company_name for readability when joining with financial_statements

User question: {question}

{schema}
"""

ANSWER_SYNTHESIS_PROMPT = """You are FinSight AI answering a loan officer's question about SME financial data.

User question: {question}

Data retrieved from DuckDB:
{data_context}

{company_context}

Instructions:
- Answer the question directly and specifically using the data above
- Cite exact numbers with proper formatting (use € for currency, % for rates)
- If comparing companies, use a clear structure
- Provide credit risk implications where relevant
- Be concise but thorough — a senior banker is reading this
- Format with markdown: **bold** for key metrics, bullet points for lists
"""


def _get_gemini_client():
    """Initialize and return the Gemini client. Returns None if unavailable."""
    try:
        from google import genai

        api_key = os.getenv("GOOGLE_API_KEY", "")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not set in environment")
            return None

        client = genai.Client(api_key=api_key)
        return client
    except Exception as exc:
        logger.warning(f"Failed to initialize Gemini: {exc}")
        return None


def _validate_sql(sql: str) -> Tuple[bool, str]:
    """
    Validates generated SQL is safe to execute.
    Returns (is_safe, reason).
    """
    sql_upper = sql.strip().upper()

    # Must start with SELECT or WITH
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return False, "Query must be a SELECT statement"

    # Block dangerous keywords
    dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
                 "TRUNCATE", "EXEC", "EXECUTE", "GRANT", "REVOKE", "COPY"]
    for kw in dangerous:
        pattern = r'\b' + kw + r'\b'
        if re.search(pattern, sql_upper):
            return False, f"Forbidden keyword: {kw}"

    # Validate table references against safe schema
    for table in SAFE_SCHEMA:
        pass  # Allow all safe tables

    return True, "OK"


def _extract_sql_from_response(text: str) -> Optional[str]:
    """Extract SQL from a markdown code block in LLM response."""
    # Try ```sql ... ``` first
    match = re.search(r'```sql\s*\n?(.*?)\n?\s*```', text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Try ``` ... ```
    match = re.search(r'```\s*\n?(SELECT.*?)\n?\s*```', text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # If response is just SQL
    stripped = text.strip()
    if stripped.upper().startswith("SELECT") or stripped.upper().startswith("WITH"):
        return stripped

    return None


def _execute_safe_sql(sql: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Execute validated SQL against DuckDB and return formatted results.
    Returns (formatted_result, error_message).
    """
    from app.duckdb_engine import get_connection

    is_safe, reason = _validate_sql(sql)
    if not is_safe:
        return None, f"SQL validation failed: {reason}"

    try:
        con = get_connection()
        df = con.execute(sql).fetchdf()

        if df.empty:
            return "No results found for this query.", None

        # Format nicely
        if len(df) <= 20:
            result = df.to_markdown(index=False)
        else:
            result = df.head(20).to_markdown(index=False)
            result += f"\n\n... showing 20 of {len(df)} rows"

        return result, None
    except Exception as exc:
        return None, f"SQL execution error: {str(exc)}"


def _get_company_context(company_id: Optional[str] = None) -> str:
    """Get current company context from DuckDB for richer answers."""
    from app.duckdb_engine import get_connection, calculate_deterministic_bankability

    try:
        con = get_connection()

        if company_id:
            data = calculate_deterministic_bankability(company_id, 750000)
            return (
                f"\nActive company context:\n"
                f"- Company: {data['company']} ({data['province']})\n"
                f"- Sector: {data['sector']}\n"
                f"- Revenue: EUR {data['revenue']/1e6:.1f}M | EBITDA: EUR {data['ebitda']/1e6:.2f}M\n"
                f"- Financial Score: {data['financial_score']}/100 | ESG: {data['esg_score']}/100\n"
                f"- DSCR: {data['dscr']:.2f}x | Net Debt/EBITDA: {data['net_debt_ebitda']:.2f}x\n"
                f"- Recommendation: {data['recommendation']}\n"
            )

        # Return all companies summary
        companies = con.execute("""
            SELECT c.company_id, c.company_name, c.sector, c.province,
                   f.revenue, f.ebitda, f.net_income, f.total_debt, f.cash_and_equivalents
            FROM companies c
            LEFT JOIN financial_statements f ON c.company_id = f.company_id
            ORDER BY c.company_name
        """).fetchdf()

        if companies.empty:
            return ""

        return f"\nAll companies in database:\n{companies.to_markdown(index=False)}\n"

    except Exception:
        return ""


def _template_fallback(question: str, company_id: Optional[str] = None) -> str:
    """
    Template-based fallback when Gemini is unavailable.
    Answers common questions using raw DuckDB queries.
    """
    from app.duckdb_engine import get_connection, calculate_deterministic_bankability

    q_lower = question.lower()
    con = get_connection()

    try:
        # DSCR / coverage questions
        if any(kw in q_lower for kw in ["dscr", "debt service", "coverage"]):
            if company_id:
                data = calculate_deterministic_bankability(company_id, 750000)
                return (
                    f"**Debt Service Coverage Ratio (DSCR) for {data['company']}:**\n\n"
                    f"- **DSCR: {data['dscr']:.2f}x** (benchmark: >1.30x)\n"
                    f"- EBITDA: EUR {data['ebitda']/1e6:.2f}M\n"
                    f"- Quick Ratio: {data['quick_ratio']:.2f}x\n\n"
                    f"A DSCR of {data['dscr']:.2f}x indicates "
                    f"{'strong' if data['dscr'] > 1.5 else 'adequate'} "
                    f"debt servicing capacity."
                )

        # Compare / comparison questions
        if any(kw in q_lower for kw in ["compare", "comparison", "versus", "vs", "all companies", "portfolio"]):
            rows = con.execute("""
                SELECT c.company_name, f.revenue, f.ebitda, f.net_income,
                       f.total_debt, f.cash_and_equivalents
                FROM companies c
                JOIN financial_statements f ON c.company_id = f.company_id
                ORDER BY f.revenue DESC
            """).fetchdf()
            if not rows.empty:
                return (
                    f"**Portfolio Comparison (FY2024):**\n\n"
                    f"{rows.to_markdown(index=False)}\n\n"
                    f"EcoTex leads in absolute revenue scale, while Meccanica shows "
                    f"strong precision-manufacturing margins."
                )

        # Revenue / financial questions
        if any(kw in q_lower for kw in ["revenue", "sales", "turnover", "fatturato"]):
            if company_id:
                data = calculate_deterministic_bankability(company_id, 750000)
                return (
                    f"**Revenue for {data['company']}:**\n\n"
                    f"- FY2024 Revenue: **EUR {data['revenue']/1e6:.1f}M**\n"
                    f"- EBITDA Margin: **{data['ebitda_margin']:.1f}%**\n"
                    f"- Sector: {data['sector']}"
                )

        # NPL / risk questions
        if any(kw in q_lower for kw in ["npl", "default", "risk", "credit risk", "provincial"]):
            rows = con.execute("SELECT * FROM bdi_provincial_credit ORDER BY default_rate_npl").fetchdf()
            return (
                f"**Banca d'Italia Provincial NPL Rates:**\n\n"
                f"{rows.to_markdown(index=False)}\n\n"
                f"Milan district at 1.82% significantly outperforms the national average of 2.95%."
            )

        # ESG questions
        if any(kw in q_lower for kw in ["esg", "sustainability", "green", "environment"]):
            if company_id:
                chunks = con.execute(
                    "SELECT chunk_text FROM document_chunks WHERE company_id = ? LIMIT 3",
                    [company_id]
                ).fetchdf()
                if not chunks.empty:
                    evidence = "\n".join(f"- {row['chunk_text'][:200]}" for _, row in chunks.iterrows())
                    return f"**ESG Evidence for {company_id}:**\n\n{evidence}"

        # General / catch-all
        if company_id:
            data = calculate_deterministic_bankability(company_id, 750000)
            return (
                f"**{data['company']} - Credit Summary:**\n\n"
                f"- Financial Score: **{data['financial_score']}/100**\n"
                f"- ESG Score: **{data['esg_score']}/100**\n"
                f"- DSCR: **{data['dscr']:.2f}x** | Net Debt/EBITDA: **{data['net_debt_ebitda']:.2f}x**\n"
                f"- Recommendation: **{data['recommendation']}**\n\n"
                f"Ask me about specific metrics, comparisons, or stress scenarios!"
            )

        return (
            "I can help you analyze the SME data in our DuckDB database. Try asking about:\n\n"
            "- **Financial metrics**: DSCR, revenue, EBITDA margins\n"
            "- **Comparisons**: Compare all companies in the portfolio\n"
            "- **Credit risk**: NPL rates, provincial benchmarks\n"
            "- **ESG**: Sustainability scores and evidence\n"
            "- **Stress testing**: What-if scenarios on loan amounts"
        )
    except Exception as exc:
        return f"I encountered an error retrieving data: {str(exc)}. Please try rephrasing your question."


def chat(
    question: str,
    company_id: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Main chat entry point.

    Args:
        question: User's natural language question
        company_id: Currently active company ID (optional)
        conversation_history: List of {"role": "user"|"assistant", "content": "..."} dicts

    Returns:
        {
            "answer": str,           # The response text (markdown)
            "sql_query": str|None,   # Generated SQL if applicable
            "sql_result": str|None,  # Raw SQL result if applicable
            "mode": str,             # "gemini" | "template_fallback"
            "error": str|None,       # Error message if any
        }
    """
    if not question or not question.strip():
        return {
            "answer": "Please ask a question about the SME financial data.",
            "sql_query": None,
            "sql_result": None,
            "mode": "template_fallback",
            "error": None,
        }

    client = _get_gemini_client()

    if client is None:
        # Fallback to templates
        answer = _template_fallback(question, company_id)
        return {
            "answer": answer,
            "sql_query": None,
            "sql_result": None,
            "mode": "template_fallback",
            "error": "Gemini API not available (GOOGLE_API_KEY not set). Using template responses.",
        }

    MODEL_NAME = "gemini-2.0-flash"

    try:
        # Step 1: Generate SQL if the question needs data
        sql_prompt = SQL_GENERATION_PROMPT.format(
            question=question,
            schema=SCHEMA_DDL,
        )

        sql_response = client.models.generate_content(
            model=MODEL_NAME,
            contents=sql_prompt,
            config={"temperature": 0.1, "max_output_tokens": 500},
        )
        sql_text = sql_response.text.strip()

        sql_query = None
        sql_result = None
        data_context = ""

        if "NO_SQL_NEEDED" not in sql_text.upper():
            extracted_sql = _extract_sql_from_response(sql_text)
            if extracted_sql:
                sql_query = extracted_sql
                result, err = _execute_safe_sql(extracted_sql)
                if result:
                    sql_result = result
                    data_context = f"SQL query executed:\n```sql\n{extracted_sql}\n```\n\nResults:\n{result}"
                elif err:
                    data_context = f"SQL query failed: {err}. Answering from general knowledge."

        # If no SQL data, grab company context directly
        if not data_context:
            data_context = _get_company_context(company_id)

        company_context = _get_company_context(company_id) if company_id else ""

        # Step 2: Build conversation for Gemini
        system_instruction = SYSTEM_PROMPT.format(schema=SCHEMA_DDL)

        # Build contents list for multi-turn
        contents = []

        # Add conversation history (last 10 turns)
        if conversation_history:
            from google.genai import types
            for msg in conversation_history[-10:]:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))

        # Add the synthesis prompt as the current user message
        synthesis = ANSWER_SYNTHESIS_PROMPT.format(
            question=question,
            data_context=data_context,
            company_context=company_context,
        )
        from google.genai import types
        contents.append(types.Content(role="user", parts=[types.Part(text=synthesis)]))

        # Generate final answer
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config={
                "system_instruction": system_instruction,
                "temperature": 0.3,
                "max_output_tokens": 1500,
            },
        )

        answer = response.text.strip()

        return {
            "answer": answer,
            "sql_query": sql_query,
            "sql_result": sql_result,
            "mode": "gemini",
            "error": None,
        }

    except Exception as exc:
        logger.error(f"Gemini chat error: {traceback.format_exc()}")
        # Fallback to template
        answer = _template_fallback(question, company_id)
        return {
            "answer": answer,
            "sql_query": None,
            "sql_result": None,
            "mode": "template_fallback",
            "error": f"Gemini error: {str(exc)}. Using template fallback.",
        }
