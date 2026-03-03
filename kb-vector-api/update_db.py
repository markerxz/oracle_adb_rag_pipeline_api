"""
DB migration script for RAG pipeline improvements.
Safe to run multiple times (idempotent).

Migrations:
  1. Alter chunk_vector column to VECTOR(*, FLOAT32) — model-agnostic dimensions (#4)
  2. Add page_number NUMBER column to DOCUMENT_CHUNKS (#8)
"""

import oracledb
from app.core.config import settings


def run_migration():
    conn = oracledb.connect(
        user=settings.db_user,
        password=settings.db_password,
        dsn=settings.db_dsn,
        config_dir=settings.wallet_dir,
        wallet_location=settings.wallet_dir,
        wallet_password=settings.db_password
    )
    c = conn.cursor()

    # Migration 1: Widen chunk_vector to VECTOR(*, FLOAT32) to support any embedding model dimension
    print("Migration 1: Updating chunk_vector to VECTOR(*, FLOAT32)...")
    try:
        c.execute("ALTER TABLE DOCUMENT_CHUNKS MODIFY (chunk_vector VECTOR(*, FLOAT32))")
        print("  ✅ chunk_vector column updated.")
    except oracledb.DatabaseError as e:
        error, = e.args
        # ORA-00957: duplicate column name or ORA-01451/01442 variations — already correct type
        print(f"  ⚠️  Skipped (may already be altered): {error.message.strip()}")

    # Migration 2: Add page_number column
    print("Migration 2: Adding page_number column to DOCUMENT_CHUNKS...")
    try:
        c.execute("ALTER TABLE DOCUMENT_CHUNKS ADD (page_number NUMBER)")
        print("  ✅ page_number column added.")
    except oracledb.DatabaseError as e:
        error, = e.args
        if error.code == 1430:  # ORA-01430: column being added already exists
            print("  ⚠️  Skipped: page_number column already exists.")
        else:
            raise

    conn.commit()
    c.close()
    conn.close()
    print("\n✅ DB migration complete.")


if __name__ == "__main__":
    run_migration()
