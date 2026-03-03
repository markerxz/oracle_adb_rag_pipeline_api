from fastapi import APIRouter, File, UploadFile, Depends, Form, HTTPException
from app.services import storage, extractor, embedder, database
from datetime import datetime
import oracledb
import uuid
import re

router = APIRouter()

def chunk_text_by_words(text: str, max_words: int):
    # Split text into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = []
    current_words = 0
    
    for sentence in sentences:
        word_count = len(sentence.split())
        if current_words + word_count > max_words and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_words = 0
            
        # If a single sentence is larger than max_words, we need to split it by words
        if word_count > max_words:
            words = sentence.split()
            for i in range(0, len(words), max_words):
                chunks.append(" ".join(words[i:i+max_words]))
        else:
            current_chunk.append(sentence)
            current_words += word_count
            
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks


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
    
    # Extract Text
    pdf_text = extractor.extract_text_from_pdf(contents)
    
    # Run Chunking in Python memory
    raw_chunks = chunk_text_by_words(pdf_text, chunk_size)
    
    response_chunks = []
    for i, text in enumerate(raw_chunks, 1):
        response_chunks.append({
            "chunk_id": i,
            "text": text
        })
        
    return {
        "message": "Chunk Preview generated successfully",
        "chunking_config": {
            "strategy": "PYTHON_WORDS",
            "max": chunk_size
        },
        "chunks_processed": len(raw_chunks),
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
        
        # 4. Chunking using Python Logic instead of constrained Oracle Algorithms
        raw_chunks = chunk_text_by_words(pdf_text, chunk_size)
        
        response_chunks = []
        for i, text in enumerate(raw_chunks, 1):
            response_chunks.append({
                "chunk_id": i,
                "text": text
            })
            
            # 5. Embedding Natively to the target Knowledge Base lock
            vec_str = embedder.get_embedding_string(text, override_model=kb_embedder)
            
            cursor.execute("""
                INSERT INTO DOCUMENT_CHUNKS (chunk_id, document_id, kb_id, chunk_vector, chunk_text)
                VALUES (:cid, :doc_id, :kb_id, TO_VECTOR(:vec), :txt)
            """, {'cid': i, 'doc_id': doc_id, 'kb_id': kb_id, 'vec': vec_str, 'txt': text})
        
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
            "strategy": "PYTHON_WORDS",
            "max": chunk_size
        },
        "chunks_processed": len(raw_chunks),
        "chunks": response_chunks
    }
