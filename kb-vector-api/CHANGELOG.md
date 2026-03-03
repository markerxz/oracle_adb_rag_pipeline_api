# Changelog

All notable changes to the **Knowledge Base & Vector Search API** are documented here.

Format: `[VERSION] — YYYY-MM-DD`

---

## [1.2.0] — 2026-03-03

### Added
- **Chunk Overlap** — Adjacent chunks now share a configurable overlap window (default: 15 words) to prevent context loss at chunk boundaries. `upload.py`
- **HyDE-lite Query Rewriting** — Question-style queries are automatically rewritten into declarative form before dense embedding, improving recall alignment with document phrasing. `search.py`
- **BM25 In-Memory Cache** — BM25 index is now built once per Knowledge Base and cached in RAM. Automatically invalidated when documents are uploaded or deleted. `search.py`
- **Multilingual Tokenizer** — BM25 now uses `pythainlp` for Thai word segmentation with a Latin fallback, replacing the naive whitespace split. `search.py`
- **Dynamic CE Candidate Pool** — Cross-Encoder reranking now receives `max(20, top_k × 5)` candidates instead of a hardcoded 10. `search.py`
- **Chunk Page Numbers** — Each ingested chunk now stores the originating PDF page number. Returned in all search results and chunk preview. `extractor.py`, `upload.py`, `schemas.py`
- **PDF Cleaning** — Extractor now strips repeated page headers/footers (detected across pages) and fixes hyphenated line-break artifacts. `extractor.py`
- **`/api/v1/config/version` endpoint** — Returns current API version and full changelog. `config.py`
- **New dependencies**: `rank_bm25==0.2.2`, `pythainlp==5.0.5`

### Changed
- `extractor.py` now returns `List[Tuple[int, str]]` (page_number, text) instead of a single string — all callers (`upload.py`) updated.
- `update_db.py` rewritten as an **idempotent migration script** (no longer drops tables). Adds `page_number` column.
- `init_db.py` schema updated: `chunk_vector VECTOR(*, FLOAT32)` (model-agnostic, applies to new installations), `page_number NUMBER` column added.
- Upload and preview endpoints now accept `overlap_size` parameter (default: 15 words).
- Chunking strategy label changed from `PYTHON_WORDS` → `PYTHON_WORDS_OVERLAP`.

### Fixed
- BM25 index was rebuilt from scratch on every single search request (O(N) per query). Now O(1) from cache.
- BM25 tokenizer failed to handle Thai text — words were unsplit, producing near-zero BM25 scores for Thai queries.
- Cross-Encoder received only 10 candidates regardless of `top_k`, limiting reranker effectiveness at higher `top_k` values.

### Notes
- **DB migration required**: Run `python update_db.py` to add the `page_number` column to existing deployments.
- Existing indexed chunks will have `page_number = NULL` until re-ingested.
- Oracle 23ai does not support `ALTER TABLE MODIFY` on `VECTOR` columns (ORA-51859). Existing tables stay at `VECTOR(384, FLOAT32)`; new installations get `VECTOR(*, FLOAT32)`.

---

## [1.1.0] — 2026-03-02

### Added
- **Hybrid Search** — Combined Dense (VECTOR_DISTANCE) + Sparse (BM25) retrieval with Reciprocal Rank Fusion (RRF).
- **Cross-Encoder Reranking** — `sentence-transformers` CrossEncoder as final reranking stage.
- **OCI Object Storage integration** — Raw PDF files stored in Oracle Cloud Object Storage.
- **Multi-KB support** — Multiple independent Knowledge Bases, each locked to a specific embedding model.
- **Hot-swap model loading** — Embedder and reranker models load lazily and swap in/out with OOM protection.
- **Setup automation** — `setup.sh` script for one-shot environment and dependency installation.
- **Oracle Wallet support** — Wallet-based TLS connection to Oracle Autonomous DB.
- **Chunk preview endpoint** — `POST /api/v1/documents/preview` to inspect chunking without ingestion.

### Changed
- Connection management upgraded to Oracle Connection Pool (min=2, max=10).
- CLOBs fetched inline via `oracledb.defaults.fetch_lobs = False` for performance.

---

## [1.0.0] — 2026-03-01

### Added
- Initial release.
- PDF ingestion via PyMuPDF (`fitz`).
- Sentence-boundary word-count chunking.
- Dense vector embedding with `sentence-transformers`.
- Vector storage in Oracle 23ai (`VECTOR` type).
- `VECTOR_DISTANCE(COSINE)` semantic search.
- FastAPI REST API with `/docs` Swagger UI.
- Oracle DB connection with wallet.
- Knowledge Bases, Documents, and Chunks data model.
