from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_dsn: Optional[str] = None
    wallet_dir: str = "/opt/kb-vector-api/wallet"
    oci_config_file: str = "/etc/kb-vector-api/oci/config"
    oci_config_profile: str = "DEFAULT"
    oci_bucket_name: Optional[str] = None
    embedder_model: str = "all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    default_chunk_size: int = 1500
    default_overlap_size: int = 15
    typhoon_api_key: Optional[str] = None

    class Config:
        env_file = "/etc/kb-vector-api/.env"

settings = Settings()
