"""Manual document upload: chunking, storage, and retrievability."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion.document_upload import (
    CHUNK_CHARS,
    UnsupportedDocument,
    chunk_text,
    delete_document,
    extract_text,
    list_uploaded_documents,
    resolve_company_id,
    store_document,
)
from ingestion.loaders import seed_database
from rag.retrieval import search_documents


@pytest.fixture(scope="module", autouse=True)
def seeded():
    seed_database(ROOT / "data" / "finsight.duckdb")


def test_chunk_short_text_is_single_chunk():
    assert chunk_text("A short covenant note.") == ["A short covenant note."]


def test_chunk_empty_text():
    assert chunk_text("   \n  ") == []


def test_chunk_long_text_respects_size_and_word_boundaries():
    text = " ".join(["covenant"] * 900)

    chunks = chunk_text(text)

    assert len(chunks) > 1
    assert all(len(c) <= CHUNK_CHARS for c in chunks)
    assert not any(c.startswith(" ") or c.endswith(" ") for c in chunks)


def test_chunking_covers_all_content():
    text = " ".join(f"term{i}" for i in range(400))

    chunks = chunk_text(text)

    assert "term0" in chunks[0]
    assert "term399" in chunks[-1]


def test_extract_text_from_txt():
    assert "DSCR" in extract_text("note.txt", b"Covenant requires DSCR above 1.3x")


def test_extract_text_rejects_unsupported_type():
    with pytest.raises(UnsupportedDocument, match="Unsupported file type"):
        extract_text("scan.xlsx", b"\x00\x01")


def test_resolve_company_id_finds_seeded_company():
    assert resolve_company_id("EcoTex") == "ecotex-001"


def test_store_rejects_unknown_company():
    """An unresolved company_id would make the document silently unretrievable."""
    with pytest.raises(UnsupportedDocument, match="No company matching"):
        store_document("note.txt", b"some text", company_name="Nonexistent SpA")


def test_uploaded_document_becomes_retrievable_evidence():
    content = (
        b"Board minutes: the supervisory board approved a revolving credit facility "
        b"with a springing covenant tied to quarterly leverage headroom."
    )

    result = store_document("board_minutes.txt", content, company_name="EcoTex Milano")
    try:
        assert result["chunks"] >= 1
        assert result["company_id"] == "ecotex-001"

        hits = search_documents("springing covenant leverage headroom", company_name="EcoTex Milano")

        assert any("springing covenant" in h["text"] for h in hits)
        assert any(h["source"] == "board_minutes.txt" for h in hits)
    finally:
        delete_document(result["document_id"])


def test_reupload_replaces_chunks_instead_of_duplicating():
    content = b"Supplier concentration risk is elevated in the northern logistics corridor."

    first = store_document("risk.txt", content, company_name="EcoTex Milano")
    second = store_document("risk.txt", content, company_name="EcoTex Milano")
    try:
        assert first["document_id"] == second["document_id"]
        listed = [d for d in list_uploaded_documents() if d["document_id"] == first["document_id"]]
        assert len(listed) == 1
        assert listed[0]["chunks"] == second["chunks"]
    finally:
        delete_document(first["document_id"])


def test_delete_removes_document_from_index():
    result = store_document("temp.txt", b"Temporary appraisal note.", company_name="EcoTex Milano")

    delete_document(result["document_id"])

    assert result["document_id"] not in [d["document_id"] for d in list_uploaded_documents()]


def test_upload_does_not_disturb_seeded_documents():
    """Uploads must add evidence, never replace the seeded ESG report."""
    result = store_document("extra.txt", b"Additional lender memo.", company_name="EcoTex Milano")
    try:
        hits = search_documents("sustainability carbon emissions", company_name="EcoTex Milano")
        assert hits, "seeded ESG chunks should still be retrievable after an upload"
    finally:
        delete_document(result["document_id"])


def test_upload_reaches_bm25_evidence():
    """The end-to-end point of uploading: chunks are retrievable via BM25."""
    content = (
        b"EcoTex Milano sustainability audit addendum: verified scope 2 emissions "
        b"reduction of 18 percent following the equipment retrofit, with third-party "
        b"assurance covering the sustainability-linked loan margin ratchet."
    )
    result = store_document(
        "esg_addendum.txt",
        content,
        company_name="EcoTex Milano",
        document_type="ESG / Sustainability Report",
    )
    try:
        hits = search_documents("scope 2 emissions retrofit", company_name="EcoTex Milano")
        assert any("esg_addendum.txt" in h["source"] for h in hits)
    finally:
        delete_document(result["document_id"])
