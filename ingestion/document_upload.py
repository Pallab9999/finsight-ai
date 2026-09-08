"""Manual document upload for loan officers.

Uploaded files are chunked into the same `documents` table the seeded ESG report
uses, so BM25 retrieval picks them up as grounded evidence with no change to the
retrieval or scoring path.

`load_all_documents` joins documents to `company_financials` when filtering by
company, so a chunk with an unresolved company_id would be silently invisible.
`resolve_company_id` is therefore mandatory before storing.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from backend.config import settings
from ingestion.loaders import create_duckdb_schema, get_connection

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = (".pdf", ".txt", ".md", ".csv", ".docx")

CHUNK_CHARS = 900
CHUNK_OVERLAP = 120


class UnsupportedDocument(Exception):
    """Raised when a file type cannot be parsed."""


def extract_text(filename: str, data: bytes) -> str:
    """Extract plain text from an uploaded file."""
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        try:
            import io

            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise UnsupportedDocument(
                "PDF support needs the pypdf package (pip install pypdf)."
            ) from exc

        reader = PdfReader(io.BytesIO(data))
        pages = [(page.extract_text() or "") for page in reader.pages]
        text = "\n".join(pages)
        if not text.strip():
            raise UnsupportedDocument(
                f"{filename} has no extractable text layer. It is likely a scanned "
                "image, which needs OCR rather than text extraction."
            )
        return text

    if suffix == ".docx":
        try:
            import io

            import docx
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise UnsupportedDocument(
                "DOCX support needs the python-docx package (pip install python-docx)."
            ) from exc

        document = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in document.paragraphs)

    if suffix in (".txt", ".md", ".csv"):
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise UnsupportedDocument(f"Could not decode {filename} as text.")

    raise UnsupportedDocument(
        f"Unsupported file type '{suffix}'. Supported: {', '.join(SUPPORTED_SUFFIXES)}."
    )


def chunk_text(text: str, chunk_chars: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks on word boundaries.

    Overlap keeps a sentence that straddles a boundary retrievable from either
    chunk, which matters because BM25 scores each chunk independently.
    """
    normalized = " ".join(text.split())
    if not normalized:
        return []
    if len(normalized) <= chunk_chars:
        return [normalized]

    step = max(1, chunk_chars - overlap)
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        window = normalized[start : start + chunk_chars]
        # Avoid cutting mid-word unless this is the final chunk.
        if start + chunk_chars < len(normalized) and " " in window:
            window = window[: window.rfind(" ")]
        chunk = window.strip()
        if chunk:
            chunks.append(chunk)
        start += max(step, len(window))
    return chunks


def resolve_company_id(company_name: str) -> str | None:
    """Look up the company_id a document should attach to."""
    conn = get_connection(settings.duckdb_path)
    try:
        row = conn.execute(
            "SELECT company_id FROM company_financials WHERE company_name ILIKE ? LIMIT 1",
            [f"%{company_name}%"],
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def list_companies() -> list[str]:
    """Companies a document can be attached to."""
    conn = get_connection(settings.duckdb_path)
    try:
        create_duckdb_schema(conn)
        rows = conn.execute(
            "SELECT DISTINCT company_name FROM company_financials ORDER BY company_name"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def store_document(
    filename: str,
    data: bytes,
    company_name: str,
    document_type: str = "Uploaded Document",
) -> dict:
    """Parse, chunk and store an uploaded document.

    Returns a result dict describing what was stored. Raises UnsupportedDocument
    if the file cannot be parsed or the company cannot be resolved.
    """
    company_id = resolve_company_id(company_name)
    if not company_id:
        raise UnsupportedDocument(
            f"No company matching '{company_name}' exists in company_financials, so "
            "the document would not be retrievable. Seed the company first."
        )

    text = extract_text(filename, data)
    chunks = chunk_text(text)
    if not chunks:
        raise UnsupportedDocument(f"{filename} produced no text to index.")

    digest = hashlib.sha256(data).hexdigest()[:12]
    document_id = f"upload-{digest}"
    uploaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    conn = get_connection(settings.duckdb_path)
    try:
        create_duckdb_schema(conn)
        # Re-uploading the same file replaces its chunks instead of duplicating them.
        conn.execute("DELETE FROM documents WHERE document_id = ?", [document_id])
        for index, chunk in enumerate(chunks, start=1):
            conn.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    document_id,
                    company_id,
                    filename,
                    document_type,
                    f"{document_id}-c{index}",
                    chunk,
                    json.dumps(
                        {
                            "origin": "manual_upload",
                            "uploaded_at": uploaded_at,
                            "sha256_prefix": digest,
                            "chunk": index,
                            "chunk_count": len(chunks),
                        }
                    ),
                ],
            )
    finally:
        conn.close()

    return {
        "document_id": document_id,
        "filename": filename,
        "company_id": company_id,
        "company_name": company_name,
        "document_type": document_type,
        "chunks": len(chunks),
        "characters": len(" ".join(chunks)),
        "uploaded_at": uploaded_at,
    }


def list_uploaded_documents() -> list[dict]:
    """Uploaded documents currently indexed, newest first."""
    conn = get_connection(settings.duckdb_path)
    try:
        create_duckdb_schema(conn)
        rows = conn.execute(
            """
            SELECT d.document_id, d.source_name, d.document_type,
                   COUNT(*) AS chunks, ANY_VALUE(c.company_name) AS company_name,
                   ANY_VALUE(d.metadata) AS metadata
            FROM documents d
            LEFT JOIN company_financials c ON d.company_id = c.company_id
            WHERE d.document_id LIKE 'upload-%'
            GROUP BY d.document_id, d.source_name, d.document_type
            """
        ).fetchall()
    finally:
        conn.close()

    results = []
    for row in rows:
        try:
            metadata = json.loads(row[5]) if row[5] else {}
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        results.append(
            {
                "document_id": row[0],
                "filename": row[1],
                "document_type": row[2],
                "chunks": row[3],
                "company_name": row[4],
                "uploaded_at": metadata.get("uploaded_at", ""),
            }
        )
    return sorted(results, key=lambda r: r["uploaded_at"], reverse=True)


def delete_document(document_id: str) -> int:
    """Remove an uploaded document's chunks. Returns rows deleted."""
    conn = get_connection(settings.duckdb_path)
    try:
        before = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE document_id = ?", [document_id]
        ).fetchone()[0]
        conn.execute("DELETE FROM documents WHERE document_id = ?", [document_id])
        return int(before)
    finally:
        conn.close()
