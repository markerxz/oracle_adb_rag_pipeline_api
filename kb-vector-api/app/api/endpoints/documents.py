from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from typing import List
from app.models.schemas import DocumentResponse
from app.services import storage, database
import urllib.parse

router = APIRouter()

@router.get("", response_model=List[DocumentResponse])
async def list_documents():
    """
    Returns a list of all documents currently ingested in the knowledge base.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, kb_id, filename, upload_date, oci_object_name 
              FROM DOCUMENTS 
          ORDER BY upload_date DESC
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append(DocumentResponse(
                id=row[0],
                kb_id=row[1],
                filename=row[2],
                upload_date=row[3],
                oci_object_name=row[4],
                size_bytes=0 # Size aggregation omitted for brevity
            ))
            
    except Exception as e:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
        
    cursor.close()
    conn.close()
    
    return results

@router.get("/{document_id}/download")
async def download_document_file(document_id: str):
    """
    Streams the original PDF document from OCI Storage for in-browser preview.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT oci_object_name, filename FROM DOCUMENTS WHERE id = :id", {'id': document_id})
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    oci_object_name, filename = row[0], row[1]
    
    try:
        content = storage.download_document(oci_object_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch document from OCI: {e}")
        
    encoded_filename = urllib.parse.quote(filename)
    
    return Response(
        content=content, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"inline; filename*=utf-8''{encoded_filename}"}
    )

@router.get("/{document_id}/chunks")
async def list_document_chunks(document_id: str):
    """
    Returns all text chunks and their corresponding embedding vectors for a specific document.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    # Check if doc exists
    cursor.execute("SELECT id FROM DOCUMENTS WHERE id = :id", {'id': document_id})
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found.")
        
    cursor.execute("""
        SELECT chunk_id, chunk_text, FROM_VECTOR(chunk_vector) as vec
          FROM DOCUMENT_CHUNKS 
         WHERE document_id = :id
      ORDER BY chunk_id ASC
    """, {'id': document_id})
    
    chunks = []
    for row in cursor.fetchall():
        text_clob = row[1]
        text = text_clob.read() if hasattr(text_clob, 'read') else text_clob
        
        vec_clob = row[2]
        vec_str = vec_clob.read() if hasattr(vec_clob, 'read') else vec_clob
        
        chunks.append({
            "chunk_id": row[0],
            "text": text,
            "vector": vec_str
        })
        
    cursor.close()
    conn.close()
    
    return {"document_id": document_id, "chunks": chunks}

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
        
        # 2. Delete Vector Chunks (Cascade manually for safety, serially)
        cursor.execute("DELETE /*+ NO_PARALLEL */ FROM DOCUMENT_CHUNKS WHERE document_id = :id", {'id': document_id})
        
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
