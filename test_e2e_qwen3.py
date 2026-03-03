import requests
import time
import os

API_URL = "http://localhost:8000/api/v1"
TEST_FILE = "/home/opc/vector-playground/documents/2.3.6.1 ทรัพย์สินประเภทที่ธนาคารรับเป็นหลักประกัน.pdf"

print("Starting E2E Validation Test...")
print(f"Targeting File: {TEST_FILE}")

# 1. Create a Knowledge Base
kb_name = f"Test E2E Qwen3 {int(time.time())}"
print(f"\\n[1] Creating KB: '{kb_name}'")
res = requests.post(f"{API_URL}/kbs", json={
    "name": kb_name,
    "description": "Automated verification test for 1500 chunk sizes and Qwen3 vector ingestion"
})
res.raise_for_status()
kb_id = res.json()["id"]
embedding_model = res.json()["embedding_model"]
print(f" -> Created KB ID: {kb_id}")
print(f" -> Locked Embedder: {embedding_model}")

# 2. Upload Document
print(f"\\n[2] Ingesting Document with Chunk Size = 1500")
with open(TEST_FILE, 'rb') as f:
    files = {
        'file': (os.path.basename(TEST_FILE), f, 'application/pdf')
    }
    data = {
        'kb_id': kb_id,
        'chunk_size': 1500
    }
    start = time.time()
    res = requests.post(f"{API_URL}/documents", files=files, data=data)
    res.raise_for_status()
    upload_data = res.json()
    
print(f" -> Upload Success in {time.time() - start:.2f}s!")
print(f" -> Oracle Fallback Config Strategy: {upload_data['chunking_config']}")
print(f" -> Total Chunks Processed: {upload_data['chunks_processed']}")

# 3. Vector Search with dynamic Qwen3 Reranker
print(f"\\n[3] Triggering Vector Search with Reranker override")
query = "หลักประกันมีอะไรบ้าง?" # "What are the collaterals?"
search_payload = {
    "kb_id": kb_id,
    "query_text": query,
    "top_k": 3,
    "reranker_model": "Qwen/Qwen3-Reranker-0.6B"
}
start = time.time()
res = requests.post(f"{API_URL}/search", json=search_payload)
res.raise_for_status()
search_data = res.json()

print(f" -> Search Success in {time.time() - start:.2f}s!")
print(f" -> Query: '{query}'")
print(f" -> Embedder Engine Tag: {search_data['embedding_model']}")
print(f" -> Reranker Engine Tag: {search_data['reranker_model']}")

print(f"\\nTop 3 Reranked Results ({search_data['reranker_model']}):")
for i, chunk in enumerate(search_data['results']):
    print(f" [{i+1}] Score: {chunk['ce_score']:.4f} | RRF: {chunk['rrf_score']:.4f}")
    print(f"     Text Preview: {chunk['chunk_text'][:100]}...")

print("\\n✅ All Automated End-to-End Tests Passed successfully!")
