"""Document chunk storage helpers."""

from pathlib import Path

from backend.config import settings
from ingestion.loaders import get_connection


def load_all_documents(company_name: str | None = None) -> list[dict]:
    conn = get_connection(settings.duckdb_path)
    try:
        if company_name:
            rows = conn.execute(
                """
                SELECT d.document_id, d.company_id, d.source_name, d.document_type,
                       d.chunk_id, d.text_content, d.metadata, c.company_name
                FROM documents d
                LEFT JOIN company_financials c ON d.company_id = c.company_id
                WHERE c.company_name ILIKE ?
                """,
                [f"%{company_name}%"],
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT document_id, company_id, source_name, document_type, "
                "chunk_id, text_content, metadata, NULL FROM documents"
            ).fetchall()

        return [
            {
                "document_id": r[0],
                "company_id": r[1],
                "source_name": r[2],
                "document_type": r[3],
                "chunk_id": r[4],
                "text_content": r[5],
                "metadata": r[6],
            }
            for r in rows
        ]
    finally:
        conn.close()
