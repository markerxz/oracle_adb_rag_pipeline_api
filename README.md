# 🧠 KB Vector — Oracle RAG Pipeline

A production-ready **Retrieval-Augmented Generation (RAG)** pipeline built on Oracle Autonomous Database 23ai. Upload PDF documents, generate semantic vector embeddings, and run state-of-the-art hybrid search — all through a clean React UI or REST API.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📁 **Multi-Collection KBs** | Isolated Knowledge Bases, each with a locked embedding model for vector space consistency |
| 📄 **Unlimited Chunking** | Custom Python regex splitter — no Oracle word limits. Configurable chunk size from the UI |
| 🔍 **Hybrid Search** | Dense Vector + BM25 Sparse merged via Reciprocal Rank Fusion (RRF), then Cross-Encoder reranked |
| 🗑 **Full KB Deletion** | One click — cascades across Oracle DB and OCI Object Storage |
| 🌐 **Swagger UI** | Auto-generated interactive API docs at `/docs` |

---

## 🏗 Architecture

```
PDF Upload ──► Python Chunker ──► SentenceTransformer ──► Oracle VECTOR Column
                                                               │
User Query ──► Dense Vector Search ─┐                         │
           ──► BM25 Sparse Search ──┼──► RRF Fusion ──► Cross-Encoder Rerank ──► Top-K Results
                                   ─┘
```

| Layer | Technology |
|---|---|
| **API** | FastAPI + Uvicorn |
| **Database** | Oracle Autonomous Database 23ai |
| **Object Storage** | OCI Object Storage |
| **Embedder** | `all-MiniLM-L6-v2` (SentenceTransformers) |
| **Sparse Search** | BM25 (`rank_bm25`) |
| **Reranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| **Frontend** | React + Vite |

---

## 🚀 Quick Start

**Prerequisites:** Python 3.9+, Node.js 18+, Oracle ADB 23ai, OCI tenancy, and your [Oracle Wallet `.zip`](https://docs.oracle.com/en-us/iaas/autonomous-database-shared/doc/connect-download-customer-managed-wallet.html) downloaded from OCI Console.

```bash
git clone https://github.com/markerxz/oracle_adb_rag_pipeline_api.git
cd oracle_adb_rag_pipeline_api
chmod +x setup.sh && ./setup.sh
```

`setup.sh` will interactively:
- Prompt for your Oracle DB and OCI credentials → generate `.env`
- Extract your Wallet zip → `wallet/`
- Install Python dependencies and download AI models
- Install React frontend dependencies

**Run the API:**
```bash
cd kb-vector-api && source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Run the UI** (separate terminal):
```bash
cd kb-vector-ui && npm run dev -- --host
```

| Service | URL |
|---|---|
| React UI | `http://localhost:5173` |
| Swagger Docs | `http://localhost:8000/docs` |

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/config/health` | Health check (DB + OCI) |
| `POST` | `/api/v1/config/embedder` | Update embedder / chunk size config |
| `POST` | `/api/v1/kbs` | Create a Knowledge Base |
| `GET` | `/api/v1/kbs` | List all Knowledge Bases |
| `DELETE` | `/api/v1/kbs/{kb_id}` | Delete KB (cascades DB + OCI) |
| `POST` | `/api/v1/documents` | Upload & vectorize a PDF |
| `POST` | `/api/v1/documents/preview` | Preview chunks without saving |
| `GET` | `/api/v1/documents/{id}/chunks` | View stored vector chunks |
| `GET` | `/api/v1/documents/{id}/download` | Download original PDF from OCI |
| `DELETE` | `/api/v1/documents/{id}` | Delete a document |
| `POST` | `/api/v1/search` | Hybrid vector search with reranking |

---

## 📦 Stack

`fastapi` · `uvicorn` · `pydantic-settings` · `sentence-transformers` · `rank-bm25` · `oracledb` · `oci` · `pymupdf` · `react` · `vite` · `axios`
