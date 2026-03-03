from fastapi import APIRouter, File, UploadFile, Depends, Form, HTTPException
from app.services import storage, extractor, embedder, database
from datetime import datetime
import oracledb
import uuid

router = APIRouter()

@router.post("/preview")
async def preview_document_chunks(
    chunk_size: int = Form(50, description="Maximum words per chunk"),
    file: UploadFile = File(...)
):
    """
    Extracts text and runs the Oracle VECTOR_CHUNKS algorithm in-memory to preview 
    how the document will be split, without saving anything to the DB or generating vectors.
    """
    contents = await file.read()
    
    # Oracle natively maxes at 1000 words per chunk for its C text processor logic
    chunk_size = min(chunk_size, 1000)
    
    # Extract Text
    pdf_text = extractor.extract_text_from_pdf(contents)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Run Chunking (Oracle DB VECTOR_CHUNKS) in memory
        cursor.setinputsizes(rec_text=oracledb.DB_TYPE_CLOB)
        preview_sql = f"""
            SELECT vc.chunk_offset, vc.chunk_text
            FROM (SELECT :rec_text AS txt FROM dual) s,
                 VECTOR_CHUNKS(
                    dbms_vector_chain.utl_to_text(s.txt) 
                    BY words MAX {chunk_size} OVERLAP 0 
                    SPLIT BY sentence LANGUAGE american NORMALIZE all
                 ) vc
        """
        cursor.execute(preview_sql, {'rec_text': pdf_text})
        
        chunks = cursor.fetchall()
        
        response_chunks = []
        for cid, ctext in chunks:
            text = ctext.read() if hasattr(ctext, 'read') else ctext
            response_chunks.append({
                "chunk_id": cid,
                "text": text
            })
            
    finally:
        cursor.close()
        conn.close()
        
    return {
        "message": "Chunk Preview generated successfully",
        "chunking_config": {
            "strategy": "WORDS",
            "max": chunk_size
        },
        "chunks_processed": len(chunks),
        "chunks": response_chunks
    }

@router.post("")
async def upload_document(
    kb_id: str = Form(..., description="The ID of the Knowledge Base to attach this document to"),
    chunk_size: int = Form(50, description="Maximum words per chunk"),
    file: UploadFile = File(...)
):
    """
    Ingest a PDF document, store it in OCI, extract text, 
    chunk it via Oracle DB, and save vector embeddings.
    """
    # 0. Validate KB Exists
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, embedding_model FROM KNOWLEDGE_BASES WHERE id = :id", {'id': kb_id})
    row = cursor.fetchone()
    if not row:
         cursor.close()
         conn.close()
         raise HTTPException(status_code=404, detail=f"Knowledge Base {kb_id} not found.")
    
    kb_embedder = row[1]

    contents = await file.read()
    
    # Oracle natively maxes at 1000 words per chunk for its C text processor logic
    chunk_size = min(chunk_size, 1000)
    
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
        insert_sql = f"""
            INSERT /*+ NO_PARALLEL */ INTO DOCUMENT_CHUNKS (chunk_id, document_id, kb_id, chunk_text)
            SELECT vc.chunk_offset, :doc_id, :kb_id, vc.chunk_text
            FROM (SELECT :rec_text AS txt FROM dual) s,
                 VECTOR_CHUNKS(
                    dbms_vector_chain.utl_to_text(s.txt) 
                    BY words MAX {chunk_size} OVERLAP 0 
                    SPLIT BY sentence LANGUAGE american NORMALIZE all
                 ) vc
        """
        cursor.execute(insert_sql, {'doc_id': doc_id, 'kb_id': kb_id, 'rec_text': pdf_text})
        
        # 5. Embedding
        cursor.execute("SELECT chunk_id, chunk_text FROM DOCUMENT_CHUNKS WHERE document_id = :doc_id", {'doc_id': doc_id})
        chunks = cursor.fetchall()
        
        response_chunks = []
        for cid, ctext in chunks:
            text = ctext.read() if hasattr(ctext, 'read') else ctext
            response_chunks.append({
                "chunk_id": cid,
                "text": text
            })
            vec_str = embedder.get_embedding_string(text, override_model=kb_embedder)
            
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
        "message": "Upload, chunking, and embedding successful",
        "document_id": doc_id,
        "oci_object_name": oci_object_name,
        "chunking_config": {
            "strategy": "WORDS",
            "max": chunk_size
        },
        "chunks_processed": len(chunks),
        "chunks": response_chunks
    }
