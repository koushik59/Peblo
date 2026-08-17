"""
Cloudflare R2 / S3-compatible object storage implementation.

Implements the Storage abstract base class using aioboto3/boto3.
Cloudflare R2 is fully S3-compatible, allowing seamless drop-in replacement
for local filesystem storage in production with zero business logic changes.
"""
from typing import Optional
from app.storage.base import Storage


class R2Storage(Storage):
    """
    Cloudflare R2 / AWS S3 storage provider.
    Connects to R2 via S3-compatible API endpoint.
    """

    def __init__(
        self,
        account_id: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        public_url: str = "",
    ):
        self.account_id = account_id
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket_name = bucket_name
        self.public_url = public_url.rstrip("/")
        self.endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"

    def _get_client(self):
        """Lazy initialization of boto3 S3 client for R2."""
        import boto3
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name="auto",
        )

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload object to R2 bucket."""
        client = self._get_client()
        client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    async def get(self, key: str) -> Optional[bytes]:
        """Download object bytes from R2 bucket."""
        client = self._get_client()
        try:
            response = client.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"].read()
        except Exception:
            return None

    async def delete(self, key: str) -> bool:
        """Delete object from R2 bucket."""
        client = self._get_client()
        try:
            client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        """Check if object exists in R2 bucket."""
        client = self._get_client()
        try:
            client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def get_public_url(self, key: str) -> str:
        """Return the public CDN / worker URL for the stored key."""
        if self.public_url:
            return f"{self.public_url}/{key}"
        return f"{self.endpoint_url}/{self.bucket_name}/{key}"

    async def atomic_rename(self, src_key: str, dst_key: str) -> bool:
        """
        Atomic copy & delete for S3 / Cloudflare R2 object store.
        """
        client = self._get_client()
        try:
            # Copy source to destination atomically in R2
            client.copy_object(
                Bucket=self.bucket_name,
                CopySource={"Bucket": self.bucket_name, "Key": src_key},
                Key=dst_key,
            )
            # Remove source object
            client.delete_object(Bucket=self.bucket_name, Key=src_key)
            return True
        except Exception:
            return False
