from fastapi import APIRouter
from app.models.schemas import SearchQuery, SearchResponse
from app.services import database, embedder

router = APIRouter()

@router.post("", response_model=SearchResponse)
async def search_documents(query: SearchQuery):
    """
    Converts natural language into a vector and performs similarity search against the DB.
    """
    # Generate vector
    vec_str = embedder.get_embedding_string(query.query_text)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    # Query Oracle securely using kb_id to isolate the search
    cursor.execute("""
        SELECT chunk_id, chunk_text, VECTOR_DISTANCE(chunk_vector, TO_VECTOR(:qv), COSINE) as dist
          FROM DOCUMENT_CHUNKS
         WHERE chunk_vector IS NOT NULL
           AND kb_id = :kb_id
      ORDER BY dist ASC 
         FETCH FIRST :top_k ROWS ONLY
    """, {'qv': vec_str, 'kb_id': query.kb_id, 'top_k': query.top_k})
    
    results = []
    for rank, (cid, raw_text, dist) in enumerate(cursor.fetchall()):
        text = raw_text.read() if hasattr(raw_text, 'read') else raw_text
        results.append({
            "rank": rank + 1,
            "chunk_id": cid,
            "distance": round(dist, 4),
            "text": text.strip().replace('\\n', ' ')
        })
        
    cursor.close()
    conn.close()
    
    return SearchResponse(kb_id=query.kb_id, query=query.query_text, results=results)
