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
                    chunk_vector VECTOR(384, FLOAT32),
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
