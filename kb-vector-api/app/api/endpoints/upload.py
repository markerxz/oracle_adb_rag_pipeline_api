from fastapi import APIRouter, File, UploadFile, Depends, Form, HTTPException
from app.services import storage, extractor, embedder, database
from datetime import datetime
import oracledb
import uuid
import re
from typing import List, Tuple

router = APIRouter()

# BM25 cache invalidation on upload
from app.api.endpoints import search as search_module


def chunk_text_by_words(
    pages: List[Tuple[int, str]],
    max_words: int,
    overlap_words: int = 15,
) -> List[Tuple[int, str]]:
    """
    Splits a list of (page_number, text) tuples into overlapping chunks.

    Each chunk is a (page_number, chunk_text) tuple where page_number is the
    page from which the chunk's first sentence originates.

    Overlap: the last `overlap_words` words of each completed chunk are carried
    over as the beginning of the next chunk to prevent context loss at boundaries.
    """
    # Flatten pages into a list of (page_num, sentence) pairs
    sentence_items: List[Tuple[int, str]] = []
    for page_num, text in pages:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sent in sentences:
            if sent.strip():
                sentence_items.append((page_num, sent.strip()))

    chunks: List[Tuple[int, str]] = []
    current_sentences: List[str] = []
    current_words = 0
    current_page = sentence_items[0][0] if sentence_items else 1
    overlap_carry: List[str] = []  # words carried from previous chunk

    def flush_chunk():
        nonlocal current_sentences, current_words, overlap_carry
        if current_sentences:
            full_text = " ".join(overlap_carry + current_sentences) if overlap_carry else " ".join(current_sentences)
            chunks.append((current_page, full_text.strip()))
            # Compute overlap words to carry into next chunk
            all_words = full_text.split()
            overlap_carry = all_words[-overlap_words:] if len(all_words) > overlap_words else all_words
        current_sentences = []
        current_words = 0

    first = True
    for page_num, sentence in sentence_items:
        word_count = len(sentence.split())

        # Start tracking page from first sentence of new chunk
        if not current_sentences:
            current_page = page_num

        if current_words + word_count > max_words and current_sentences:
            flush_chunk()

        # Handle sentences that are themselves longer than max_words
        if word_count > max_words:
            words = sentence.split()
            for i in range(0, len(words), max_words):
                sub = " ".join(words[i:i + max_words])
                carry = " ".join(overlap_carry) if overlap_carry else ""
                full_sub = (carry + " " + sub).strip() if carry else sub
                chunks.append((page_num, full_sub))
                overlap_carry = words[i:i + max_words][-overlap_words:]
            overlap_carry = words[-overlap_words:]
        else:
            current_sentences.append(sentence)
            current_words += word_count

    flush_chunk()
    return chunks


@router.post("/preview")
async def preview_document_chunks(
    chunk_size: int = Form(50, description="Maximum words per chunk"),
    overlap_size: int = Form(15, description="Overlap words between chunks"),
    file: UploadFile = File(...),
):
    """
    Extracts text and previews how the document will be chunked,
    including per-chunk page numbers and overlap.
    """
    contents = await file.read()
    pages = extractor.extract_text_from_pdf(contents)
    raw_chunks = chunk_text_by_words(pages, chunk_size, overlap_size)

    response_chunks = []
    for i, (page_num, text) in enumerate(raw_chunks, 1):
        response_chunks.append({
            "chunk_id": i,
            "page_number": page_num,
            "text": text
        })

    return {
        "message": "Chunk preview generated successfully",
        "chunking_config": {
            "strategy": "PYTHON_WORDS_OVERLAP",
            "max_words": chunk_size,
            "overlap_words": overlap_size,
        },
        "chunks_processed": len(raw_chunks),
        "chunks": response_chunks,
    }


@router.post("")
async def upload_document(
    kb_id: str = Form(..., description="The ID of the Knowledge Base to attach this document to"),
    chunk_size: int = Form(50, description="Maximum words per chunk"),
    overlap_size: int = Form(15, description="Overlap words between adjacent chunks"),
    file: UploadFile = File(...),
):
    """
    Ingest a PDF document, store it in OCI, extract + clean text,
    chunk it with overlap, and save page-aware vector embeddings.
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

    # 2. Extract Text (returns list of (page_num, text) tuples, cleaned)
    pages = extractor.extract_text_from_pdf(contents)

    # 3. Create Unique Document Record
    doc_id = str(uuid.uuid4())

    try:
        cursor.execute("""
            INSERT INTO DOCUMENTS (id, kb_id, filename, upload_date, oci_object_name)
            VALUES (:id, :kbid, :fname, :udate, :oname)
        """, {
            'id': doc_id, 'kbid': kb_id, 'fname': file.filename,
            'udate': datetime.now(), 'oname': oci_object_name
        })

        # 4. Chunk with overlap — each chunk carries its originating page number
        raw_chunks = chunk_text_by_words(pages, chunk_size, overlap_size)

        response_chunks = []
        for i, (page_num, text) in enumerate(raw_chunks, 1):
            response_chunks.append({
                "chunk_id": i,
                "page_number": page_num,
                "text": text,
            })

            # 5. Embed chunk using KB-locked model
            vec_str = embedder.get_embedding_string(text, override_model=kb_embedder)

            cursor.execute("""
                INSERT INTO DOCUMENT_CHUNKS (chunk_id, document_id, kb_id, chunk_vector, chunk_text, page_number)
                VALUES (:cid, :doc_id, :kb_id, TO_VECTOR(:vec), :txt, :pnum)
            """, {
                'cid': i, 'doc_id': doc_id, 'kb_id': kb_id,
                'vec': vec_str, 'txt': text, 'pnum': page_num,
            })

        conn.commit()
    except Exception as e:
        conn.rollback()
        storage.delete_document(oci_object_name)
        raise e
    finally:
        cursor.close()
        conn.close()

    # Invalidate BM25 cache for this KB so next search rebuilds the index
    search_module.invalidate_bm25_cache(kb_id)

    return {
        "message": "Upload, chunking, and embedding successful",
        "document_id": doc_id,
        "oci_object_name": oci_object_name,
        "chunking_config": {
            "strategy": "PYTHON_WORDS_OVERLAP",
            "max_words": chunk_size,
            "overlap_words": overlap_size,
        },
        "chunks_processed": len(raw_chunks),
        "chunks": response_chunks,
    }
