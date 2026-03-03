from fastapi import APIRouter, HTTPException
from typing import List
from app.models.schemas import KBBase, KBResponse
from app.services import database, embedder
from datetime import datetime
import uuid

router = APIRouter()

@router.post("", response_model=KBResponse)
async def create_knowledge_base(kb_in: KBBase):
    """
    Create a new Collection/Knowledge Base.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    kb_id = str(uuid.uuid4())
    create_time = datetime.now()
    
    active_model = embedder.get_current_model_name()
    
    try:
        cursor.execute("""
            INSERT INTO KNOWLEDGE_BASES (id, name, description, created_at, embedding_model)
            VALUES (:id, :name, :description, :ctime, :embedding_model)
        """, {
            'id': kb_id, 
            'name': kb_in.name, 
            'description': kb_in.description, 
            'ctime': create_time,
            'embedding_model': active_model
        })
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
        
    return KBResponse(id=kb_id, name=kb_in.name, description=kb_in.description, created_at=create_time, embedding_model=active_model)

@router.get("", response_model=List[KBResponse])
async def list_knowledge_bases():
    """
    Returns a list of all existing Knowledge Bases.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, description, created_at, embedding_model
          FROM KNOWLEDGE_BASES 
      ORDER BY created_at DESC
    """)
    
    kbs = []
    for row in cursor.fetchall():
        kb_id = row[0]
        kbs.append({
            "id": kb_id,
            "name": row[1],
            "description": row[2],
            "created_at": row[3],
            "embedding_model": row[4] or "Unknown",
            "documents": [],
            "chunk_count": 0
        })
        
    for kb in kbs:
        # Fetch Documents for this KB
        cursor.execute("""
            SELECT id, filename, upload_date, oci_object_name 
            FROM DOCUMENTS WHERE kb_id = :kb_id
        """, {'kb_id': kb['id']})
        
        for doc in cursor.fetchall():
            kb['documents'].append({
                "id": doc[0],
                "filename": doc[1],
                "upload_date": doc[2],
                "oci_object_name": doc[3]
            })
            
        # Count total chunks for this KB
        cursor.execute("""
            SELECT COUNT(*) FROM DOCUMENT_CHUNKS WHERE kb_id = :kb_id
        """, {'kb_id': kb['id']})
        kb['chunk_count'] = cursor.fetchone()[0] or 0
        
    results = [KBResponse(**kb) for kb in kbs]
        
    cursor.close()
    conn.close()
    
    return results
