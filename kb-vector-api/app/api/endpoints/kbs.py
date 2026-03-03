from fastapi import APIRouter, HTTPException
from typing import List
from app.models.schemas import KBBase, KBResponse
from app.services import database
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
    
    try:
        cursor.execute("""
            INSERT INTO KNOWLEDGE_BASES (id, name, description, created_at)
            VALUES (:id, :name, :description, :ctime)
        """, {
            'id': kb_id, 
            'name': kb_in.name, 
            'desc': kb_in.description, 
            'ctime': create_time
        })
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
        
    return KBResponse(id=kb_id, name=kb_in.name, description=kb_in.description, created_at=create_time)

@router.get("", response_model=List[KBResponse])
async def list_knowledge_bases():
    """
    Returns a list of all existing Knowledge Bases.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, description, created_at 
          FROM KNOWLEDGE_BASES 
      ORDER BY created_at DESC
    """)
    
    results = []
    for row in cursor.fetchall():
        results.append(KBResponse(
            id=row[0],
            name=row[1],
            description=row[2],
            created_at=row[3]
        ))
        
    cursor.close()
    conn.close()
    
    return results
