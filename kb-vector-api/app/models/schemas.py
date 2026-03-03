from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# --- Knowledge Base Schemas ---

class KBBase(BaseModel):
    name: str = Field(..., description="Name of the Knowledge Base collection (e.g. 'HR Policies')")
    description: Optional[str] = Field(None, description="Optional description of the collection")

class KBResponse(KBBase):
    id: str
    created_at: datetime
    embedding_model: str
    chunk_count: int = 0
    documents: List[dict] = []

# --- Document Schemas ---

class DocumentResponse(BaseModel):
    id: str
    kb_id: str
    filename: str
    upload_date: datetime
    oci_object_name: str
    size_bytes: int

# --- Search Schemas ---

class ChunkResponse(BaseModel):
    rank: int
    chunk_id: int
    distance: float
    chunk_text: str
    document_id: str
    document_filename: str
    page_number: Optional[int] = None

class SearchQuery(BaseModel):
    kb_id: str = Field(..., description="The highly specific ID of the Knowledge Base to search within.")
    query_text: str = Field(..., description="The natural language question to search the knowledge base for.")
    top_k: int = Field(3, description="Number of results to return.")
    reranker_model: Optional[str] = Field(None, description="Optional Cross-Encoder model override for this specific search.")

class SearchResponse(BaseModel):
    kb_id: str
    query: str
    embedding_model: str
    reranker_model: str
    results: List[ChunkResponse]
