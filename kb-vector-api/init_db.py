import oracledb
from app.core.config import settings

def init_db():
    print("Connecting to Oracle DB...")
    connection = oracledb.connect(
        user=settings.db_user,
        password=settings.db_password,
        dsn=settings.db_dsn,
        config_dir=settings.wallet_dir,
        wallet_location=settings.wallet_dir,
        wallet_password=settings.db_password
    )
    cursor = connection.cursor()

    try:
        # Create KNOWLEDGE_BASES Table
        print("Creating KNOWLEDGE_BASES table...")
        cursor.execute("""
            CREATE TABLE KNOWLEDGE_BASES (
                id VARCHAR2(36) PRIMARY KEY,
                name VARCHAR2(255) NOT NULL,
                description VARCHAR2(1000),
                created_at TIMESTAMP NOT NULL
            )
        """)
    except oracledb.DatabaseError as e:
        error, = e.args
        if error.code == 955:
            print("KNOWLEDGE_BASES table already exists.")
        else:
            raise

    try:
        # Create DOCUMENTS Table
        print("Creating DOCUMENTS table...")
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
    except oracledb.DatabaseError as e:
        error, = e.args
        if error.code == 955: # ORA-00955: name is already used by an existing object
            print("DOCUMENTS table already exists.")
        else:
            raise

    try:
        # Create DOCUMENT_CHUNKS Table
        print("Creating DOCUMENT_CHUNKS table...")
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
    except oracledb.DatabaseError as e:
        error, = e.args
        if error.code == 955:
            print("DOCUMENT_CHUNKS table already exists.")
        else:
            raise

    connection.commit()
    cursor.close()
    connection.close()
    print("✅ Database initialization complete.")

if __name__ == "__main__":
    init_db()
