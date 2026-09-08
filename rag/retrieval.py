"""Keyword-based document retrieval (BM25)."""

from rank_bm25 import BM25Okapi

from rag.documents import load_all_documents


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def search_documents(query: str, company_name: str | None = None, top_k: int = 3) -> list[dict]:
    docs = load_all_documents(company_name)
    if not docs:
        return []

    corpus = [_tokenize(d["text_content"]) for d in docs]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(_tokenize(query))

    ranked = sorted(
        zip(docs, scores, strict=False),
        key=lambda x: x[1],
        reverse=True,
    )[:top_k]

    results = []
    for doc, score in ranked:
        if score <= 0:
            continue
        results.append(
            {
                "source": doc["source_name"],
                "document_type": doc["document_type"],
                "chunk_id": doc["chunk_id"],
                "text": doc["text_content"],
                "score": round(float(score), 3),
            }
        )
    return results
