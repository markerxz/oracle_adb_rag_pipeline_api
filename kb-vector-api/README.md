# Knowledge Base & Vector Search API

A production-ready FastAPI backend for unstructured document ingestion and semantic search. It utilizes Oracle Autonomous Database for Vector Search capabilities and OCI Object Storage for raw file retention.

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- Python 3.9+
- An Oracle DB Wallet unzipped to `/home/opc/vector-playground/wallet`
- An OCI Config file setup (`~/.oci/config`) with access to your tenancy.

### 2. Installation
```bash
git clone <your-repo-url>
cd kb-vector-api

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Setup
Create a `.env` file in the root directory:
```env
DB_PASSWORD="YOUR_DB_PASSWORD"
OCI_BUCKET_NAME="YOUR_STORAGE_BUCKET_NAME"
# Optional overrides:
# DB_USER="ADMIN"
# DB_DSN="adbforailowercost_high"
# OCI_CONFIG_PROFILE="DEFAULT"
```

### 4. Database Setup
Initialize the required Oracle tables:
```bash
python init_db.py
```

### 5. Running the API
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📖 API Documentation (Swagger UI)
Once running, navigate your browser to:
**`http://127.0.0.1:8000/docs`**

The interactive Swagger UI allows you to test the API directly:
1. `POST /api/v1/kbs` -> **Create** a new Knowledge Base collection
2. `GET /api/v1/kbs` -> **List** all available Knowledge Bases
3. `POST /api/v1/documents` -> **Upload** a PDF into a specific KB
4. `POST /api/v1/search` -> **Search** a specific KB using vectors
5. `GET /api/v1/documents` -> **List** indexed documents
6. `DELETE /api/v1/documents/{id}` -> **Safely remove** a document & its vectors
