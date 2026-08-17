"""
Storage factory module.

Provides get_storage() to dynamically instantiate the configured storage provider
(LocalStorage or Cloudflare R2 / S3) based on environment configuration.
"""
from app.core.config import settings
from app.storage.base import Storage
from app.storage.local import LocalStorage


def get_storage() -> Storage:
    """
    Factory function returning the configured Storage provider.
    Swapping between LocalStorage and Cloudflare R2 requires only setting
    STORAGE_BACKEND=r2 with credentials in .env.
    """
    if settings.storage_backend.lower() in ("r2", "s3"):
        from app.storage.r2 import R2Storage
        return R2Storage(
            account_id=settings.r2_account_id,
            access_key_id=settings.r2_access_key_id,
            secret_access_key=settings.r2_secret_access_key,
            bucket_name=settings.r2_bucket_name,
            public_url=settings.r2_public_url,
        )
    return LocalStorage(settings.storage_path)


__all__ = ["Storage", "LocalStorage", "get_storage"]
