from fastapi import APIRouter, File, UploadFile, Depends, Form, HTTPException
from app.services import storage, extractor, embedder, database
from datetime import datetime
import oracledb
import uuid

router = APIRouter()

@router.post("")
async def upload_document(
    kb_id: str = Form(..., description="The ID of the Knowledge Base to attach this document to"),
    file: UploadFile = File(...)
):
    """
    Ingest a PDF document, store it in OCI, extract text, 
    chunk it via Oracle DB, and save vector embeddings.
    """
    # 0. Validate KB Exists
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM KNOWLEDGE_BASES WHERE id = :id", {'id': kb_id})
    if not cursor.fetchone():
         cursor.close()
         conn.close()
         raise HTTPException(status_code=404, detail=f"Knowledge Base {kb_id} not found.")

    contents = await file.read()
    
    # 1. Upload Original File to OCI Object Storage
    oci_object_name = storage.upload_document(contents, file.filename)
    
    # 2. Extract Text
    pdf_text = extractor.extract_text_from_pdf(contents)
    
    # 3. Create Unique Document Record
    doc_id = str(uuid.uuid4())
    
    try:
        # Save Metadata
        cursor.execute("""
            INSERT INTO DOCUMENTS (id, kb_id, filename, upload_date, oci_object_name)
            VALUES (:id, :kbid, :fname, :udate, :oname)
        """, {
            'id': doc_id, 'kbid': kb_id, 'fname': file.filename, 
            'udate': datetime.now(), 'oname': oci_object_name
        })
        
        # 4. Chunking (Oracle DB VECTOR_CHUNKS)
        cursor.setinputsizes(rec_text=oracledb.DB_TYPE_CLOB)
        cursor.execute("""
            INSERT INTO DOCUMENT_CHUNKS (chunk_id, document_id, kb_id, chunk_text)
            SELECT :size + vc.chunk_offset, :doc_id, :kb_id, vc.chunk_text
            FROM (SELECT :rec_text AS txt FROM dual) s,
                 VECTOR_CHUNKS(dbms_vector_chain.utl_to_text(s.txt) BY words MAX 50) vc
        """, {'doc_id': doc_id, 'kb_id': kb_id, 'size': 50, 'rec_text': pdf_text})
        
        # 5. Embedding
        cursor.execute("SELECT chunk_id, chunk_text FROM DOCUMENT_CHUNKS WHERE document_id = :doc_id", {'doc_id': doc_id})
        chunks = cursor.fetchall()
        
        for cid, ctext in chunks:
            text = ctext.read() if hasattr(ctext, 'read') else ctext
            vec_str = embedder.get_embedding_string(text)
            
            cursor.execute("""
                UPDATE DOCUMENT_CHUNKS 
                   SET chunk_vector = TO_VECTOR(:vec)
                 WHERE document_id = :doc_id AND chunk_id = :cid
            """, {'doc_id': doc_id, 'cid': cid, 'vec': vec_str})
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        # Rollback OCI upload if DB fails
        storage.delete_document(oci_object_name)
        raise e
    finally:
        cursor.close()
        conn.close()
        
    return {
        "message": "Upload & Embedding successful",
        "document_id": doc_id,
        "chunks_processed": len(chunks)
    }
