# KB Vector Application - V1.1 🚀

Welcome to **KB Vector App V1.1**. This release brings massive stability, flexibility, and architectural enhancements to the enterprise AI Retrieval-Augmented Generation (RAG) pipeline!

## 🌟 What's New in V1.1

### 1. Unlimited Python-Native Document Chunking
We have officially **removed the Oracle Database 1000-word ceiling limiter** from `VECTOR_CHUNKS` native ingestion. 
- The backend API now utilizes a custom Python Regex boundary-splitter that intelligently parses paragraphs based on semantic sentence boundaries (`.!?`).
- The **Default Words per Chunk** is now fully customizable from the frontend Embedder Configuration page, and allows you to scale massive LLM payload ingestion arrays (e.g. `1500+` words per chunk) with zero OCI ingestion friction!

### 2. Immutable Knowledge Bases
- Each newly created Knowledge Base (KB) now permanently locks its **Dense Embedding Model** (e.g., `all-MiniLM-L6-v2`) in the Oracle Database upon creation. 
- You can now freely alter default embedding configurations in the UI without risking Vector Space drift or catastrophic Semantic Search failures across older collections.

### 3. Dynamic Precision Reranking (RRF)
- The `/search` query API now features state-of-the-art **Reciprocal Rank Fusion (RRF)**, merging Sparse Keyword retrieval capabilities (via BM25) and Dense Cosine Vectors. 
- You can dynamically inject any Cross-Encoder LLM (e.g., `BAAI/bge-reranker-base`) at runtime from the Vector Search page dropdown to forcefully re-evaluate search accuracy in real time!

### 4. Bulletproof Memory Scaling
- Completely re-architected the `SentenceTransformer` loading mechanism inside the backend container to aggressively leverage mutually exclusive Python `Garbage Collection (GC)` cycles. 
- The VM can now reliably hotswap AI models in and out of 1GB memory spaces cleanly without triggering native Linux `OOMKiller` events.

## 🛠 Required Stack
* Oracle Database 23ai (Configured via DSN Wallet)
* OCI Object Storage
* FastAPI
* React + Vite Node.js GUI

## 🚀 Setting Up the Application

Navigate into the UI folder to launch the GUI portal using `npm run dev --host`, and ensure the `kb-vector-api` system daemon is running underneath to connect all pipeline infrastructure.
