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
    text: str

class SearchQuery(BaseModel):
    kb_id: str = Field(..., description="The highly specific ID of the Knowledge Base to search within.")
    query_text: str = Field(..., description="The natural language question to search the knowledge base for.")
    top_k: int = Field(3, description="Number of results to return.")

class SearchResponse(BaseModel):
    kb_id: str
    query: str
    results: List[ChunkResponse]
