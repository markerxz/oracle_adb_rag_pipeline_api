# Oracle ADB RAG Pipeline API

This repository contains a full-stack Retrieval-Augmented Generation (RAG) pipeline built natively on **Oracle Autonomous Database (ADB)** using **VECTOR_DISTANCE** and **Oracle Cloud Infrastructure (OCI) Object Storage**.

## Features

- **Multi-Tenant Knowledge Bases**: Create and isolate multiple Vector Document collections.
- **State-of-the-Art Hybrid Search (RRF)**: Fuses Oracle Dense Vector Distance with fast, in-memory Sparse BM25 keyword matching using Reciprocal Rank Fusion.
- **Cross-Encoder Reranking**: Re-evaluates top hybrid-search candidate chunks using the lightweight `cross-encoder/ms-marco-MiniLM-L-6-v2` LLM model for deep contextual synergy without GPU bottlenecks.
- **Native Oracle Vector Database**: Fully leverages Oracle 23ai native Vector datatype and CLOB inline text retrieval for blazingly fast querying.
- **Interactive UI**: A sleek, dark-mode React frontend for uploading, chunking, parsing, and testing Semantic Search visually.
- **Deep-Linked PDF Previews**: View your original source documents securely with inline browser previewing straight from OCI, automatically anchored to the matched search chunks.

## Project Structure

- `/kb-vector-api` - FastAPI Backend (Python)
- `/kb-vector-ui` - React Frontend (Vite)

## API Walkthrough

### 1. Database & OCI Config
**POST `/api/v1/config/database`** & **POST `/api/v1/config/oci`**
Uploads securely mount `wallet.zip` and OCI Private Key files to the server's `.env` space without requiring hardcoded server strings.

### 2. Embedder Config
**POST `/api/v1/config/embedder`**
Set the primary Dense Vector model. (Default is `all-MiniLM-L6-v2`).

*(Note: While tested with standard SentenceTransformers, some newer Multi-Modal VL models like Qwen3-VL are not strictly compatible out-of-the-box with text-only encoding APIs without custom pooling abstraction.)*

### 3. Knowledge Base
**POST `/api/v1/kbs`**
Creates a new isolated vector collection to group documents logically.

### 4. Document Ingestion
**POST `/api/v1/documents/preview`** (Preview Chunks)
**POST `/api/v1/documents`** (Vectorize & Save)
Uploads PDF files directly into OCI Object Storage securely, extracts the text using PyPDF2, partitions intelligently into semantic chunks, encodes using the active SentenceTransformer model, and saves to Oracle DB as raw Vector types.

### 5. Semantic Vector Search
**POST `/api/v1/search`**
Expects `{"kb_id": "...", "query_text": "...", "top_k": 5}`.
Reroutes through:
1. Fast Oracle `VECTOR_DISTANCE` top-K search.
2. In-memory `BM25Okapi` Exact Keyword match search.
3. RRF (Reciprocal Rank Fusion) combination.
4. Final contextual reranking output.

## Running Locally

### Backend
```bash
cd kb-vector-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd kb-vector-ui
npm install
npm run dev
```

## Version
Main v.1.0 
