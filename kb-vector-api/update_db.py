import oracledb
from app.core.config import settings
def fix_db():
    conn = oracledb.connect(
        user=settings.db_user, password=settings.db_password, dsn=settings.db_dsn,
        config_dir=settings.wallet_dir, wallet_location=settings.wallet_dir, wallet_password=settings.db_password
    )
    c = conn.cursor()
    try: 
        c.execute("DROP TABLE DOCUMENT_CHUNKS CASCADE CONSTRAINTS")
        print("Dropped DOCUMENT_CHUNKS")
    except: pass
    try: 
        c.execute("DROP TABLE DOCUMENTS CASCADE CONSTRAINTS")
        print("Dropped DOCUMENTS")
    except: pass
    conn.commit()
    conn.close()
fix_db()
