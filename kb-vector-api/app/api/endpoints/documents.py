from fastapi import APIRouter, HTTPException
from typing import List
from app.models.schemas import DocumentResponse
from app.services import storage, database

router = APIRouter()

@router.get("", response_model=List[DocumentResponse])
async def list_documents():
    """
    Returns a list of all documents currently ingested in the knowledge base.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, filename, upload_date, oci_object_name 
          FROM DOCUMENTS 
      ORDER BY upload_date DESC
    """)
    
    results = []
    for row in cursor.fetchall():
        results.append(DocumentResponse(
            id=row[0],
            filename=row[1],
            upload_date=row[2],
            oci_object_name=row[3],
            size_bytes=0 # Size aggregation omitted for brevity
        ))
        
    cursor.close()
    conn.close()
    
    return results

@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Deletes a document completely:
    1. Removes raw file from OCI Object Storage.
    2. Removes Vector Chunks from DB.
    3. Removes Metadata from DB.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    # Locate document OCI string
    cursor.execute("SELECT oci_object_name FROM DOCUMENTS WHERE id = :id", {'id': document_id})
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    oci_object_name = row[0]
    
    try:
        # 1. Delete OCI object
        storage.delete_document(oci_object_name)
        
        # 2. Delete Vector Chunks (Cascade manually for safety)
        cursor.execute("DELETE FROM DOCUMENT_CHUNKS WHERE document_id = :id", {'id': document_id})
        
        # 3. Delete Document Metadata
        cursor.execute("DELETE FROM DOCUMENTS WHERE id = :id", {'id': document_id})
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {e}")
    finally:
        cursor.close()
        conn.close()
        
    return {"message": f"Successfully deleted document {document_id}"}
