from fastapi import APIRouter
from app.models.schemas import SearchQuery, SearchResponse
from app.services import database, embedder
from rank_bm25 import BM25Okapi
from typing import List, Dict, Any
import time

router = APIRouter()

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
    1. Dense Vector Distance (Top 50)
    2. Sparse BM25 Keyword Search (Top 50)
    3. RRF Fusion
    4. Cross-Encoder Nuance Reranking (Top 20) -> returns Top K
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
    # 1. DENSE VECTOR MATCHING
    # ---------------------------------------------------------
    query_start = time.time()
    vec_str = embedder.get_embedding_string(query.query_text, kb_embedder)
    
    cursor.execute("""
        SELECT c.chunk_id, d.id as doc_id, c.chunk_text, VECTOR_DISTANCE(c.chunk_vector, TO_VECTOR(:qv), COSINE) as dist
          FROM DOCUMENT_CHUNKS c
          JOIN DOCUMENTS d ON c.document_id = d.id
         WHERE c.chunk_vector IS NOT NULL
           AND c.kb_id = :kb_id
      ORDER BY dist ASC 
         FETCH FIRST 50 ROWS ONLY
    """, {'qv': vec_str, 'kb_id': query.kb_id})
    
    dense_results = {}
    chunk_metadata = {} # Cache doc logic to avoid re-querying
    for rank, (cid, doc_id, raw_text, dist) in enumerate(cursor.fetchall()):
        uid = f"{doc_id}_{cid}"
        dense_results[uid] = rank + 1
        text = raw_text.read() if hasattr(raw_text, 'read') else raw_text
        chunk_metadata[uid] = {"chunk_id": cid, "doc_id": doc_id, "text": text.strip().replace('\\n', ' ')}
    print(f"🕦 DENSE: {time.time() - query_start:.2f}s")
        
    # ---------------------------------------------------------
    # 2. SPARSE KEYWORD MATCHING (BM25)
    # ---------------------------------------------------------
    sparse_start = time.time()
    # Fetch all chunks for the active KB to build in-memory BM25 index
    cursor.execute("""
        SELECT c.chunk_id, d.id as doc_id, c.chunk_text, d.filename
          FROM DOCUMENT_CHUNKS c
          JOIN DOCUMENTS d ON c.document_id = d.id
         WHERE c.kb_id = :kb_id
    """, {'kb_id': query.kb_id})
    
    all_chunks = []
    sparse_corpus = []
    for cid, doc_id, raw_text, filename in cursor.fetchall():
        uid = f"{doc_id}_{cid}"
        text = raw_text.read() if hasattr(raw_text, 'read') else raw_text
        text = text.strip().replace('\\n', ' ')
        if uid not in chunk_metadata:
            chunk_metadata[uid] = {"chunk_id": cid, "doc_id": doc_id, "text": text}
        chunk_metadata[uid]["filename"] = filename # Add filename for final return
        
        all_chunks.append(uid)
        sparse_corpus.append(text.lower().split(" "))
        
    cursor.close()
    conn.close()
    
    sparse_results = {}
    if sparse_corpus:
        bm25 = BM25Okapi(sparse_corpus)
        tokenized_query = query.query_text.lower().split(" ")
        doc_scores = bm25.get_scores(tokenized_query)
        
        # Zip UIDs with scores, sort descending, grab Top 50
        ranked_sparse = sorted(zip(all_chunks, doc_scores), key=lambda x: x[1], reverse=True)[:50]
        for rank, (uid, bm25_score) in enumerate(ranked_sparse):
            if bm25_score > 0: # Only count if there is keyword overlap
                sparse_results[uid] = rank + 1
    print(f"🕦 SPARSE: {time.time() - sparse_start:.2f}s")
                
    # ---------------------------------------------------------
    # 3. RECIPROCAL RANK FUSION (RRF)
    # ---------------------------------------------------------
    rrf_start = time.time()
    rrf_scores = compute_rrf(dense_results, sparse_results)
    
    # Sort UIDs by highest RRF score and grab Top 10 Candidates (to optimize CPU inference speed)
    top_candidates = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:10]
    print(f"🕦 RRF: {time.time() - rrf_start:.2f}s")
    
    if not top_candidates:
        return SearchResponse(kb_id=query.kb_id, query=query.query_text, results=[])
        
    # ---------------------------------------------------------
    # 4. CROSS-ENCODER RERANKING
    # ---------------------------------------------------------
    ce_start = time.time()
    candidate_pairs = []
    candidate_uids = []
    for uid, _ in top_candidates:
        candidate_uids.append(uid)
        chunk_text = chunk_metadata[uid]["text"]
        candidate_pairs.append([query.query_text, chunk_text])
        
    reranker = embedder.get_cross_encoder(query.reranker_model)
    ce_scores = reranker.predict(candidate_pairs)
    
    # Zip UIDs with Reranker scores
    final_scored_results = sorted(zip(candidate_uids, ce_scores), key=lambda x: x[1], reverse=True)
    
    # ---------------------------------------------------------
    # 5. FORMAT & RETURN TOP_K
    # ---------------------------------------------------------
    response_list = []
    for rank, (uid, ce_score) in enumerate(final_scored_results[:query.top_k]):
        meta = chunk_metadata[uid]
        response_list.append({
            "rank": rank + 1,
            "chunk_id": meta["chunk_id"],
            "distance": round(float(ce_score), 4), # Converting numpy float32 to python float
            "chunk_text": meta["text"],
            "document_id": meta["doc_id"],
            "document_filename": meta.get("filename", "Unknown")
        })
    print(f"🕦 CE: {time.time() - ce_start:.2f}s")
        
    return SearchResponse(
        kb_id=query.kb_id, 
        query=query.query_text, 
        embedding_model=kb_embedder,
        reranker_model=query.reranker_model or embedder.settings.reranker_model,
        results=response_list
    )
