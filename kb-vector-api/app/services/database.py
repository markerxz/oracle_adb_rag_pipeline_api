import oracledb
from app.core.config import settings

# Drastically improves performance by fetching CLOBs directly as strings 
# instead of requiring a separate network roundtrip per locator.
oracledb.defaults.fetch_lobs = False

# Global Connection Pool
pool = None

def init_db_pool():
    global pool
    print("Initializing Oracle DB Connection Pool...")
    if not settings.db_user or not settings.db_password or not settings.db_dsn:
        print("Database credentials not fully provided. Skipping pool initialization.")
        return

    try:
        pool = oracledb.create_pool(
            user=settings.db_user,
            password=settings.db_password,
            dsn=settings.db_dsn,
            config_dir=settings.wallet_dir,
            wallet_location=settings.wallet_dir,
            wallet_password=settings.db_password,
            min=2, max=10, increment=1
        )
    except Exception as e:
        print(f"Failed to initialize Oracle DB pool: {e}")

def close_db_pool():
    global pool
    if pool:
        pool.close()

def get_db_connection():
    if not pool:
        init_db_pool()
    if not pool:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Database is not configured. Please upload credentials via /api/v1/config/database")
    return pool.acquire()
