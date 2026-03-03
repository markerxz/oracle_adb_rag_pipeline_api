from fastapi import APIRouter
from app.models.schemas import SearchQuery, SearchResponse
from app.services import database, embedder
from rank_bm25 import BM25Okapi
from typing import List, Dict, Any, Optional
import time

router = APIRouter()

# ---------------------------------------------------------
# BM25 IN-MEMORY CACHE (keyed by kb_id)
# Invalidated when docs are uploaded or deleted for a KB.
# ---------------------------------------------------------
_bm25_cache: Dict[str, Dict] = {}
# Cache entry shape: { "bm25": BM25Okapi, "uids": [...], "metadata": {...} }


def invalidate_bm25_cache(kb_id: str):
    """Remove the cached BM25 index for a KB. Called after upload/delete."""
    if kb_id in _bm25_cache:
        del _bm25_cache[kb_id]
        print(f"🗑️  BM25 cache invalidated for KB {kb_id}")


# ---------------------------------------------------------
# MULTILINGUAL TOKENIZER (#6)
# Handles Thai word segmentation + standard Latin tokenization.
# ---------------------------------------------------------
def _tokenize(text: str) -> List[str]:
    """
    Tokenizes text for BM25, handling mixed Thai/English content.
    Uses pythainlp for Thai segments, whitespace splitting for others.
    Removes punctuation-attached tokens and normalizes to lowercase.
    """
    import re
    try:
        from pythainlp.tokenize import word_tokenize as th_tokenize
        from pythainlp.util import is_thai_char

        # Detect if text contains Thai characters
        has_thai = any(is_thai_char(c) for c in text)
        if has_thai:
            tokens = th_tokenize(text.lower(), engine="newmm", keep_whitespace=False)
            # Filter out spaces, punctuation-only tokens
            return [t.strip() for t in tokens if t.strip() and not re.fullmatch(r'[\W\d]+', t.strip())]
    except ImportError:
        pass  # Fall through to basic tokenization

    # Fallback: clean whitespace tokenization with punctuation stripping
    tokens = re.sub(r'[^\w\s]', ' ', text.lower()).split()
    return [t for t in tokens if len(t) > 1]


# ---------------------------------------------------------
# QUERY REWRITING — HyDE-lite (#2)
# Rewrites the question into a declarative retrieval-friendly form.
# Bridges the vocabulary gap between question phrasing and document phrasing.
# ---------------------------------------------------------
def _rewrite_query(query_text: str) -> str:
    """
    Lightweight HyDE-lite query rewriting.
    Converts question-style queries to declarative statement style
    which better matches how knowledge is phrased in documents.

    Example:
      "What collateral does the bank accept?" →
      "The bank accepts the following types of collateral:"
    """
    import re
    q = query_text.strip()

    # Already looks like a statement — don't touch it
    if not re.search(r'\?$', q) and not re.match(r'^(what|who|when|where|why|how|which|ใคร|อะไร|ที่ไหน|เมื่อไร|ทำไม|อย่างไร)', q, re.IGNORECASE):
        return q

    # Prefix with a declarative anchor — improves dense embedding alignment
    return f"The answer to '{q}' is:"


def compute_rrf(dense_ranks: Dict[str, int], sparse_ranks: Dict[str, int], k=60) -> Dict[str, float]:
    """Computes Reciprocal Rank Fusion (RRF) for two sets of ranked document IDs."""
    rrf_scores = {}
    all_docs = set(dense_ranks.keys()).union(set(sparse_ranks.keys()))
    for doc_id in all_docs:
        dense_rank = dense_ranks.get(doc_id, float('inf'))
        sparse_rank = sparse_ranks.get(doc_id, float('inf'))
        rrf_scores[doc_id] = (1.0 / (k + dense_rank)) + (1.0 / (k + sparse_rank))
    return rrf_scores


@router.post("", response_model=SearchResponse)
async def search_documents(query: SearchQuery):
    """
    Advanced Hybrid Search Pipeline:
    1. HyDE-lite Query Rewriting
    2. Dense Vector Distance (Top 50)
    3. Sparse BM25 Keyword Search (Top 50) — cached per KB
    4. RRF Fusion
    5. Cross-Encoder Reranking (dynamic candidate pool) → returns Top K
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()

    # ---------------------------------------------------------
    # 0. FETCH KB EMBEDDER MODEL
    # ---------------------------------------------------------
    cursor.execute("SELECT embedding_model FROM KNOWLEDGE_BASES WHERE id = :id", {'id': query.kb_id})
    row = cursor.fetchone()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Knowledge Base not found")
    kb_embedder = row[0]

    # ---------------------------------------------------------
    # 1. QUERY REWRITING (HyDE-lite)
    # ---------------------------------------------------------
    rewritten_query = _rewrite_query(query.query_text)
    if rewritten_query != query.query_text:
        print(f"✏️  Query rewritten: '{query.query_text}' → '{rewritten_query}'")

    # ---------------------------------------------------------
    # 2. DENSE VECTOR MATCHING
    # ---------------------------------------------------------
    query_start = time.time()
    vec_str = embedder.get_embedding_string(rewritten_query, kb_embedder)

    cursor.execute("""
        SELECT c.chunk_id, d.id as doc_id, c.chunk_text, c.page_number,
               VECTOR_DISTANCE(c.chunk_vector, TO_VECTOR(:qv), COSINE) as dist
          FROM DOCUMENT_CHUNKS c
          JOIN DOCUMENTS d ON c.document_id = d.id
         WHERE c.chunk_vector IS NOT NULL
           AND c.kb_id = :kb_id
      ORDER BY dist ASC
         FETCH FIRST 50 ROWS ONLY
    """, {'qv': vec_str, 'kb_id': query.kb_id})

    dense_results = {}
    chunk_metadata = {}
    for rank, (cid, doc_id, raw_text, page_num, dist) in enumerate(cursor.fetchall()):
        uid = f"{doc_id}_{cid}"
        dense_results[uid] = rank + 1
        text = raw_text.read() if hasattr(raw_text, 'read') else raw_text
        chunk_metadata[uid] = {
            "chunk_id": cid, "doc_id": doc_id,
            "text": text.strip().replace('\\n', ' '),
            "page_number": page_num,
        }
    print(f"🕦 DENSE: {time.time() - query_start:.2f}s")

    # ---------------------------------------------------------
    # 3. SPARSE KEYWORD MATCHING (BM25) — with in-memory cache
    # ---------------------------------------------------------
    sparse_start = time.time()
    kb_id = query.kb_id

    if kb_id not in _bm25_cache:
        print(f"📦 BM25 cache MISS for KB {kb_id} — building index...")
        cursor.execute("""
            SELECT c.chunk_id, d.id as doc_id, c.chunk_text, d.filename, c.page_number
              FROM DOCUMENT_CHUNKS c
              JOIN DOCUMENTS d ON c.document_id = d.id
             WHERE c.kb_id = :kb_id
        """, {'kb_id': kb_id})

        all_chunks = []
        sparse_corpus = []
        for cid, doc_id, raw_text, filename, page_num in cursor.fetchall():
            uid = f"{doc_id}_{cid}"
            text = raw_text.read() if hasattr(raw_text, 'read') else raw_text
            text = text.strip().replace('\\n', ' ')
            if uid not in chunk_metadata:
                chunk_metadata[uid] = {"chunk_id": cid, "doc_id": doc_id, "text": text, "page_number": page_num}
            chunk_metadata[uid]["filename"] = filename

            all_chunks.append(uid)
            sparse_corpus.append(_tokenize(text))  # Multilingual tokenizer

        _bm25_cache[kb_id] = {
            "bm25": BM25Okapi(sparse_corpus) if sparse_corpus else None,
            "uids": all_chunks,
            "metadata": {uid: chunk_metadata[uid] for uid in all_chunks},
        }
        print(f"📦 BM25 index built: {len(all_chunks)} chunks")
    else:
        print(f"⚡ BM25 cache HIT for KB {kb_id}")
        cached = _bm25_cache[kb_id]
        # Merge cached metadata (filename etc.) into chunk_metadata for result formatting
        for uid, meta in cached["metadata"].items():
            if uid not in chunk_metadata:
                chunk_metadata[uid] = meta
            else:
                chunk_metadata[uid].setdefault("filename", meta.get("filename", "Unknown"))

    cursor.close()
    conn.close()

    cached = _bm25_cache[kb_id]
    sparse_results = {}
    if cached["bm25"] and cached["uids"]:
        tokenized_query = _tokenize(query.query_text)  # Use original query for keyword matching
        doc_scores = cached["bm25"].get_scores(tokenized_query)
        ranked_sparse = sorted(zip(cached["uids"], doc_scores), key=lambda x: x[1], reverse=True)[:50]
        for rank, (uid, bm25_score) in enumerate(ranked_sparse):
            if bm25_score > 0:
                sparse_results[uid] = rank + 1
    print(f"🕦 SPARSE: {time.time() - sparse_start:.2f}s")

    # ---------------------------------------------------------
    # 4. RECIPROCAL RANK FUSION (RRF)
    # ---------------------------------------------------------
    rrf_start = time.time()
    rrf_scores = compute_rrf(dense_results, sparse_results)

    # Dynamic candidate pool: at least 20, or 5x top_k — whichever is larger (#7)
    pool_size = min(max(20, query.top_k * 5), len(rrf_scores))
    top_candidates = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:pool_size]
    print(f"🕦 RRF: {time.time() - rrf_start:.2f}s | CE pool size: {len(top_candidates)}")

    if not top_candidates:
        return SearchResponse(kb_id=query.kb_id, query=query.query_text, results=[])

    # ---------------------------------------------------------
    # 5. CROSS-ENCODER RERANKING
    # ---------------------------------------------------------
    ce_start = time.time()
    candidate_pairs = []
    candidate_uids = []
    for uid, _ in top_candidates:
        candidate_uids.append(uid)
        chunk_text = chunk_metadata[uid]["text"]
        # Use original query for CE — CE benefits from natural question phrasing
        candidate_pairs.append([query.query_text, chunk_text])

    reranker = embedder.get_cross_encoder(query.reranker_model)
    ce_scores = reranker.predict(candidate_pairs)
    final_scored_results = sorted(zip(candidate_uids, ce_scores), key=lambda x: x[1], reverse=True)

    # ---------------------------------------------------------
    # 6. FORMAT & RETURN TOP_K
    # ---------------------------------------------------------
    response_list = []
    for rank, (uid, ce_score) in enumerate(final_scored_results[:query.top_k]):
        meta = chunk_metadata[uid]
        response_list.append({
            "rank": rank + 1,
            "chunk_id": meta["chunk_id"],
            "distance": round(float(ce_score), 4),
            "chunk_text": meta["text"],
            "document_id": meta["doc_id"],
            "document_filename": meta.get("filename", "Unknown"),
            "page_number": meta.get("page_number"),
        })
    print(f"🕦 CE: {time.time() - ce_start:.2f}s")

    return SearchResponse(
        kb_id=query.kb_id,
        query=query.query_text,
        embedding_model=kb_embedder,
        reranker_model=query.reranker_model or embedder.settings.reranker_model,
        results=response_list
    )
