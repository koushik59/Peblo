"""
Storage abstraction layer.

Provides a clean interface for file operations so that switching from local
filesystem to Cloudflare R2, S3, or any other object store requires only
a new implementation of the Storage protocol — zero changes to business logic.
"""
from abc import ABC, abstractmethod
from typing import Optional


class Storage(ABC):
    """Abstract storage interface for file operations."""

    @abstractmethod
    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Store data at the given key. Returns the storage key."""
        ...

    @abstractmethod
    async def get(self, key: str) -> Optional[bytes]:
        """Retrieve data for the given key. Returns None if not found."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete data at the given key. Returns True if deleted."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in storage."""
        ...

    @abstractmethod
    def get_public_url(self, key: str) -> str:
        """Get a URL that can be used to access the stored file."""
        ...

    @abstractmethod
    async def atomic_rename(self, src_key: str, dst_key: str) -> bool:
        """Atomically rename/move a file. Used for atomic catalogue publishing."""
        ...
