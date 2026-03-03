# 🧠 Oracle ADB RAG Pipeline — KB Vector

> **Version 1.1** — A production-ready Retrieval-Augmented Generation (RAG) API pipeline powered by Oracle Autonomous Database, OCI Object Storage, and Sentence Transformers.

---

## 📌 What is this?

This is a full-stack **Knowledge Base (KB) and Vector Search API** platform. It allows you to:

- Upload PDF documents into isolated **Knowledge Bases**
- Automatically chunk, embed into semantic vectors, and store them in **Oracle VECTOR columns**
- Run **state-of-the-art hybrid search** (Dense Vector + Sparse BM25 + Cross-Encoder Reranking) over the ingested documents
- Manage everything through a clean **React web interface** or directly via a **Swagger RESTful API**

This system is designed as the backbone for RAG pipelines — feeding retrieved context chunks directly into LLMs for grounded, document-aware answers.

---

## 🏗 Architecture

```
PDF Upload ──► Python Chunker ──► SentenceTransformer ──► Oracle VECTOR Column
                                                               │
User Query ──► Dense Vector Search ─┐                         │
           ──► BM25 Sparse Search ──┼──► RRF Fusion ──► Cross-Encoder Rerank ──► Top-K Results
                                   ─┘
```

| Component | Technology |
|---|---|
| **Backend API** | FastAPI + Uvicorn (Python 3.9) |
| **Database** | Oracle Autonomous Database 23ai |
| **Object Storage** | OCI Object Storage |
| **Dense Embedder** | `all-MiniLM-L6-v2` (SentenceTransformers) |
| **Sparse Retrieval** | BM25 (rank_bm25) |
| **Cross-Encoder Reranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| **Frontend UI** | React + Vite |

---

## ✨ Key Features

### 📁 Multi-Collection Knowledge Bases
Create separate isolated knowledge bases. Each KB locks in its Dense Embedding Model at creation time — ensuring vector space consistency even if you later change the default embedder.

### 📄 Unlimited Document Chunking
Unlike Oracle's native `VECTOR_CHUNKS` which caps at ~1000 words, this pipeline uses a **Python regex-based splitter** with intelligent sentence boundaries. Configure the default chunk size (words) freely from the UI.

### 🔍 Hybrid Search (Dense + Sparse + Reranker)
1. **Dense Vector Search** — Top 50 via Oracle `VECTOR_DISTANCE` (Cosine)
2. **BM25 Sparse Keyword Search** — Top 50 in-memory via `rank_bm25`
3. **Reciprocal Rank Fusion (RRF)** — Merges both lists into top 10 candidates
4. **Cross-Encoder Reranking** — Fine-grained semantic reranking before returning top-K results

### 🗑 Full KB Deletion
Delete a Knowledge Base in one click — cascades to remove all associated documents, vector chunks from Oracle, and original PDFs from OCI Object Storage.

### 🌐 Interactive Swagger UI
Full auto-generated API documentation available at `/docs`.

---

## 🚀 Getting Started

### Prerequisites
- Oracle Autonomous Database 23ai (with VECTOR support)
- OCI tenancy with Object Storage bucket configured
- Python 3.9+, Node.js 18+

### Backend Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/markerxz/oracle_adb_rag_pipeline_api.git
   cd oracle_adb_rag_pipeline_api
   ```

2. Set up the Python environment:
   ```bash
   cd kb-vector-api
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Configure environment variables by creating a `.env` file (see `.env.example`):
   ```env
   DB_USER=ADMIN
   DB_PASSWORD=<your_oracle_password>
   DB_DSN=<your_tns_alias>
   OCI_BUCKET_NAME=<your_bucket_name>
   EMBEDDER_MODEL=all-MiniLM-L6-v2
   RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
   ```

4. Place your Oracle Wallet in a `wallet/` directory (excluded from git) and configure `DB_CONFIG_DIR` to point to it.

5. Initialize the database schema:
   ```bash
   python init_db.py  # run once
   ```

6. Start the API:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

```bash
cd kb-vector-ui
npm install
npm run dev -- --host
```

The UI is accessible at `http://localhost:5173`.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/docs` | Interactive Swagger UI |
| `GET` | `/api/v1/config/health` | Health check (DB + OCI) |
| `POST` | `/api/v1/config/embedder` | Update default embedder/chunk config |
| `POST` | `/api/v1/kbs` | Create a new Knowledge Base |
| `GET` | `/api/v1/kbs` | List all Knowledge Bases |
| `DELETE` | `/api/v1/kbs/{kb_id}` | Delete KB (cascades DB + OCI) |
| `POST` | `/api/v1/documents` | Upload & vectorize a PDF |
| `POST` | `/api/v1/documents/preview` | Preview chunks without saving |
| `GET` | `/api/v1/documents/{id}/chunks` | View stored vector chunks |
| `GET` | `/api/v1/documents/{id}/download` | Download original PDF from OCI |
| `DELETE` | `/api/v1/documents/{id}` | Delete a document |
| `POST` | `/api/v1/search` | Hybrid vector search with reranking |

---

## 🔐 Security Notes

- **Never commit your Oracle Wallet or `.env` files.** Both are listed in `.gitignore`.
- Use environment variables or secrets management for all credentials in production.

---

## 📦 Tech Stack

- `fastapi`, `uvicorn`, `pydantic-settings`
- `sentence-transformers`, `rank-bm25`
- `oracledb`, `oci`
- `pymupdf` (PDF parsing)
- `react`, `vite`, `axios`
