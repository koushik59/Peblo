from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://peblo:peblo_secret@db:5432/peblo_tv"
    database_url_sync: str = "postgresql://peblo:peblo_secret@db:5432/peblo_tv"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 480

    # Storage
    storage_backend: str = "local"  # "local", "r2", "s3"
    storage_path: str = "/app/storage_data"

    # Cloudflare R2 / S3 Configuration
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "peblo-tv"
    r2_public_url: str = ""

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS
    cors_origins: str = "http://localhost:3001,http://localhost:3002"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
