from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.endpoints import upload, search, documents, kbs, config
from app.services.database import init_db_pool, close_db_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db_pool()
    yield
    close_db_pool()

app = FastAPI(
    title="Knowledge Base & Vector Search API",
    description="API for ingesting unstructured documents, generating vector embeddings, and semantic searching via Oracle DB.",
    version="1.3.0-beta",
    lifespan=lifespan
)

# Include Routers
app.include_router(config.router, prefix="/api/v1/config", tags=["Configuration"])
app.include_router(kbs.router, prefix="/api/v1/kbs", tags=["Knowledge Bases"])
app.include_router(upload.router, prefix="/api/v1/documents", tags=["Ingestion"])
app.include_router(search.router, prefix="/api/v1/search", tags=["Retrieval"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Management"])

@app.get("/health")
def health_check():
    return {"status": "healthy"}
