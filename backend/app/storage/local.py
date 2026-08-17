"""
Local filesystem storage implementation.

Uses the local filesystem for storing artwork and catalogue files.
Implements atomic operations via os.rename() for catalogue publishing.
"""
import os
import aiofiles
import aiofiles.os
from pathlib import Path
from typing import Optional
from app.storage.base import Storage


class LocalStorage(Storage):
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        """Resolve a key to an absolute path, preventing path traversal."""
        resolved = (self.base_path / key).resolve()
        if not str(resolved).startswith(str(self.base_path.resolve())):
            raise ValueError("Path traversal detected")
        return resolved

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        return key

    async def get(self, key: str) -> Optional[bytes]:
        path = self._resolve(key)
        if not path.exists():
            return None
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete(self, key: str) -> bool:
        path = self._resolve(key)
        if path.exists():
            await aiofiles.os.remove(path)
            return True
        return False

    async def exists(self, key: str) -> bool:
        path = self._resolve(key)
        return path.exists()

    def get_public_url(self, key: str) -> str:
        return f"/storage/{key}"

    async def atomic_rename(self, src_key: str, dst_key: str) -> bool:
        """
        Atomic rename using os.rename().
        On POSIX systems, os.rename is atomic when src and dst are on the same
        filesystem. On Windows, we use os.replace which is also atomic.
        """
        src = self._resolve(src_key)
        dst = self._resolve(dst_key)
        if not src.exists():
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(str(src), str(dst))
        return True
