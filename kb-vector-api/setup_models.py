#!/usr/bin/env python3
"""
setup_models.py — Download required AI models for the KB Vector API
Run this once before starting the server:
    python kb-vector-api/setup_models.py
"""
from sentence_transformers import SentenceTransformer, CrossEncoder

EMBEDDER_MODEL = "all-MiniLM-L6-v2"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

print(f"[1/2] Downloading embedding model: {EMBEDDER_MODEL} ...")
SentenceTransformer(EMBEDDER_MODEL)
print(f"    ✅ Done.")

print(f"[2/2] Downloading reranker model: {RERANKER_MODEL} ...")
CrossEncoder(RERANKER_MODEL)
print(f"    ✅ Done.")

print("\n🎉 All models downloaded and cached. You're ready to run the API!")
