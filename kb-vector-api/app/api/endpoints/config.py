import os
import shutil
import zipfile
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import Optional
from app.core.config import settings
from app.services import database

router = APIRouter()

@router.post("/database")
async def configure_database(
    db_user: str = Form(..., description="The Oracle DB Username (e.g., ADMIN)"),
    db_password: str = Form(..., description="The Oracle DB Password"),
    db_dsn: str = Form(..., description="The Oracle DB DSN (e.g., adbforailowercost_high)"),
    oci_bucket_name: Optional[str] = Form(None, description="The OCI Bucket Name for storing PDFs"),
    wallet_zip: UploadFile = File(..., description="The Oracle Wallet ZIP file")
):
    """
    Configure the database connection dynamically by uploading the Oracle Wallet zip and providing credentials.
    """
    # 1. Save and extract the wallet zip
    os.makedirs(settings.wallet_dir, exist_ok=True)
    wallet_zip_path = os.path.join("/tmp", wallet_zip.filename)
    
    try:
        with open(wallet_zip_path, "wb") as buffer:
            shutil.copyfileobj(wallet_zip.file, buffer)
            
        # Extract to wallet dir
        with zipfile.ZipFile(wallet_zip_path, 'r') as zip_ref:
            zip_ref.extractall(settings.wallet_dir)
            
        # Update sqlnet.ora to point to the correct directory if it exists
        sqlnet_path = os.path.join(settings.wallet_dir, "sqlnet.ora")
        if os.path.exists(sqlnet_path):
            with open(sqlnet_path, "r") as f:
                content = f.read()
            import re
            content = re.sub(r'DIRECTORY\s*=\s*"?[^"]+"?', f'DIRECTORY="{settings.wallet_dir}"', content)
            with open(sqlnet_path, "w") as f:
                f.write(content)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid wallet zip file.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process wallet: {e}")
    finally:
        if os.path.exists(wallet_zip_path):
            os.remove(wallet_zip_path)

    # 2. Update the running settings
    settings.db_user = db_user
    settings.db_password = db_password
    settings.db_dsn = db_dsn
    if oci_bucket_name:
        settings.oci_bucket_name = oci_bucket_name
    
    # 3. Save to .env file so it persists across restarts
    env_path = "/etc/kb-vector-api/.env"
    try:
        with open(env_path, "w") as f:
            f.write(f'DB_USER="{settings.db_user}"\n')
            f.write(f'DB_PASSWORD="{settings.db_password}"\n')
            f.write(f'DB_DSN="{settings.db_dsn}"\n')
            if settings.oci_bucket_name:
                f.write(f'OCI_BUCKET_NAME="{settings.oci_bucket_name}"\n')
    except Exception as e:
        print(f"Warning: Could not save .env to {env_path}: {e}")

    # 4. Re-initialize DB Pool
    try:
        database.close_db_pool()
        database.init_db_pool()
        
        # Verify connection by running a dummy query
        conn = database.get_db_connection()
        c = conn.cursor()
        c.execute("SELECT 1 FROM dual")
        c.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to Oracle DB with new credentials. Check your DSN, password, and Wallet zip. Error: {str(e)}")

    return {"message": "Database configured successfully and connection established!"}

@router.post("/database/initialize")
async def initialize_database_tables():
    """
    Once configured, build the KNOWLEDGE_BASES, DOCUMENTS, and DOCUMENT_CHUNKS tables in the database.
    """
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        tables_created = []
        try:
            cursor.execute("""
                CREATE TABLE KNOWLEDGE_BASES (
                    id VARCHAR2(36) PRIMARY KEY,
                    name VARCHAR2(255) NOT NULL,
                    description VARCHAR2(1000),
                    created_at TIMESTAMP NOT NULL
                )
            """)
            tables_created.append("KNOWLEDGE_BASES")
        except Exception as e: pass
        
        try:
            cursor.execute("""
                CREATE TABLE DOCUMENTS (
                    id VARCHAR2(36) PRIMARY KEY,
                    kb_id VARCHAR2(36) NOT NULL,
                    filename VARCHAR2(255) NOT NULL,
                    upload_date TIMESTAMP NOT NULL,
                    oci_object_name VARCHAR2(512) NOT NULL,
                    CONSTRAINT fk_kb_docs
                        FOREIGN KEY (kb_id)
                        REFERENCES KNOWLEDGE_BASES(id)
                        ON DELETE CASCADE
                )
            """)
            tables_created.append("DOCUMENTS")
        except Exception as e: pass
        
        try:
            cursor.execute("""
                CREATE TABLE DOCUMENT_CHUNKS (
                    chunk_id NUMBER,
                    document_id VARCHAR2(36),
                    kb_id VARCHAR2(36) NOT NULL,
                    chunk_text CLOB NOT NULL,
                    chunk_vector VECTOR(*, FLOAT32),
                    PRIMARY KEY (document_id, chunk_id),
                    CONSTRAINT fk_document
                        FOREIGN KEY (document_id)
                        REFERENCES DOCUMENTS(id)
                        ON DELETE CASCADE,
                    CONSTRAINT fk_kb_chunks
                        FOREIGN KEY (kb_id)
                        REFERENCES KNOWLEDGE_BASES(id)
                        ON DELETE CASCADE
                )
            """)
            tables_created.append("DOCUMENT_CHUNKS")
        except Exception as e: pass

        conn.commit()
        cursor.close()
        conn.close()
        return {"message": f"Database tables initialized. Tables created: {', '.join(tables_created) if tables_created else 'None'}"}
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Failed to initialize Oracle DB tables: {str(e)}")

@router.post("/oci")
async def configure_oci(
    user_ocid: str = Form(..., description="The OCI User OCID"),
    tenancy_ocid: str = Form(..., description="The OCI Tenancy OCID"),
    fingerprint: str = Form(..., description="The API Key Fingerprint"),
    region: str = Form(..., description="The OCI Region (e.g. us-ashburn-1)"),
    oci_bucket_name: str = Form(..., description="The OCI Bucket Name for storing PDFs"),
    private_key: UploadFile = File(..., description="The oci_api_key.pem file")
):
    """
    Configure the OCI Object Storage connection dynamically by uploading the PEM key and providing OCI credentials.
    """
    oci_dir = os.path.dirname(settings.oci_config_file)
    os.makedirs(oci_dir, exist_ok=True)
    
    key_path = os.path.join(oci_dir, "oci_api_key.pem")
    
    try:
        with open(key_path, "wb") as buffer:
            shutil.copyfileobj(private_key.file, buffer)
        
        # Ensure correct permissions for the private key
        os.chmod(key_path, 0o600)
        
        # Write the OCI config file
        config_content = f"""[DEFAULT]
user={user_ocid}
fingerprint={fingerprint}
tenancy={tenancy_ocid}
region={region}
key_file={key_path}
"""
        with open(settings.oci_config_file, "w") as f:
            f.write(config_content)
            
        os.chmod(settings.oci_config_file, 0o600)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process OCI configuration: {e}")
        
    # Update running settings and .env
    settings.oci_bucket_name = oci_bucket_name
    env_path = "/etc/kb-vector-api/.env"
    try:
        existing_lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                existing_lines = f.readlines()
        
        with open(env_path, "w") as f:
            for line in existing_lines:
                if not line.startswith("OCI_BUCKET_NAME="):
                    f.write(line)
            f.write(f'OCI_BUCKET_NAME="{settings.oci_bucket_name}"\n')
    except Exception as e:
        print(f"Warning: Could not save .env to {env_path}: {e}")

    return {"message": "OCI Object Storage Configuration saved successfully!"}

@router.get("/health")
async def get_system_health():
    """
    Actively test the connections to both the Oracle Database and OCI Object Storage.
    """
    health = {
        "database": False,
        "oci": False,
        "errors": []
    }
    
    # 1. Test Oracle DB
    try:
        conn = database.get_db_connection()
        c = conn.cursor()
        c.execute("SELECT 1 FROM dual")
        c.close()
        conn.close()
        health["database"] = True
    except Exception as e:
        health["errors"].append(f"DB Error: {str(e)}")

    # 2. Test OCI Storage
    try:
        from app.services.storage import get_object_storage_client
        client, tenancy = get_object_storage_client()
        # A simple namespace fetch proves auth works
        client.get_namespace(compartment_id=tenancy)
        health["oci"] = True
    except Exception as e:
        health["errors"].append(f"OCI Error: {str(e)}")

    return health

@router.get("/status")
async def get_config_status():
    """
    Check the current configuration status of the backend without exposing sensitive credentials.
    """
    db_configured = bool(settings.db_user and settings.db_password and settings.db_dsn and os.path.exists(settings.wallet_dir))
    oci_configured = os.path.exists(settings.oci_config_file)
    
    return {
        "database": {
            "configured": db_configured,
            "dsn": settings.db_dsn if db_configured else None,
            "user": settings.db_user if db_configured else None
        },
        "oci": {
            "configured": oci_configured,
            "bucket_name": settings.oci_bucket_name if oci_configured else None
        }
    }

from app.services import embedder
from pydantic import BaseModel

class EmbedderConfigRequest(BaseModel):
    model_name: str
    reranker_model: str
    default_chunk_size: int = 1500

@router.get("/embedder")
async def get_embedder_config():
    """Returns the currently active Vector Embedding LLM model."""
    return {
        "model_name": embedder.get_current_model_name(),
        "reranker_model": embedder.get_current_reranker_name(),
        "default_chunk_size": settings.default_chunk_size
    }

@router.post("/embedder")
async def update_embedder_config(config: EmbedderConfigRequest):
    """Updates the Vector Embedding LLM model and reloads it into memory."""
    # Validate it's a known lightweight model for safety to prevent massive downloads crashing the VM
    allowed_embedders = ["all-MiniLM-L6-v2", "all-mpnet-base-v2", "paraphrase-multilingual-MiniLM-L12-v2"]
    allowed_rerankers = ["cross-encoder/ms-marco-MiniLM-L-6-v2", "BAAI/bge-reranker-base"]
    
    if config.model_name not in allowed_embedders:
        raise HTTPException(status_code=400, detail=f"Embedder Model must be one of: {', '.join(allowed_embedders)}")
    if config.reranker_model not in allowed_rerankers:
        raise HTTPException(status_code=400, detail=f"Reranker Model must be one of: {', '.join(allowed_rerankers)}")
        
    try:
        # 1. Update .env file
        env_content = f"EMBEDDER_MODEL={config.model_name}\nRERANKER_MODEL={config.reranker_model}\nDEFAULT_CHUNK_SIZE={config.default_chunk_size}\n"
        if os.path.exists(settings.Config.env_file):
            with open(settings.Config.env_file, "r") as f:
                lines = f.readlines()
            
            # Remove existing overrides
            lines = [l for l in lines if not l.startswith("EMBEDDER_MODEL=") and not l.startswith("RERANKER_MODEL=") and not l.startswith("DEFAULT_CHUNK_SIZE=")]
            lines.append(env_content)
            
            with open(settings.Config.env_file, "w") as f:
                f.writelines(lines)
        else:
            with open(settings.Config.env_file, "w") as f:
                f.write(env_content)
                
        # 2. Update runtime settings & reload models
        settings.embedder_model = config.model_name
        settings.reranker_model = config.reranker_model
        settings.default_chunk_size = config.default_chunk_size
        embedder.setup_embedder(config.model_name, config.reranker_model)
        
        return {"message": f"Successfully loaded embedder model {config.model_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load or save model: {e}")


# ---------------------------------------------------------------------------
# VERSION & CHANGELOG
# ---------------------------------------------------------------------------
import re as _re

CHANGELOG_PATH = os.path.join(os.getcwd(), "CHANGELOG.md")

def _parse_changelog() -> list:
    """Parse CHANGELOG.md into a structured list of version entries."""
    try:
        with open(os.path.abspath(CHANGELOG_PATH), "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return []

    entries = []
    # Split on version headers: ## [X.Y.Z] — YYYY-MM-DD
    blocks = _re.split(r'\n(?=## \[\d+\.\d+\.\d+\])', content.strip())

    for block in blocks:
        header_match = _re.match(r'## \[(\d+\.\d+\.\d+)\] — (\d{4}-\d{2}-\d{2})', block)
        if not header_match:
            continue

        version_str = header_match.group(1)
        date_str = header_match.group(2)
        sections = {}

        # Parse each ### section
        section_blocks = _re.split(r'\n(?=### )', block)
        for section in section_blocks[1:]:  # skip header block
            section_match = _re.match(r'### (.+)\n([\s\S]*)', section)
            if section_match:
                section_name = section_match.group(1).strip()
                items_raw = section_match.group(2).strip()
                # Extract bullet items
                items = [
                    _re.sub(r'`[^`]+`', lambda m: m.group(0), line.lstrip("- ").strip())
                    for line in items_raw.splitlines()
                    if line.strip().startswith("- ")
                ]
                sections[section_name] = items

        entries.append({
            "version": version_str,
            "date": date_str,
            "sections": sections
        })

    return entries


@router.get("/version")
async def get_version():
    """
    Returns the current API version and the full structured changelog.
    """
    from app.main import app as _app
    changelog = _parse_changelog()
    return {
        "version": _app.version,
        "changelog": changelog
    }

