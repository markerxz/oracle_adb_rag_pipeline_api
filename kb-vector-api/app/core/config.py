from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_dsn: Optional[str] = None
    wallet_dir: str = "/opt/kb-vector-api/wallet"
    oci_config_profile: str = "DEFAULT"
    oci_bucket_name: Optional[str] = None

    class Config:
        env_file = "/etc/kb-vector-api/.env"

settings = Settings()
