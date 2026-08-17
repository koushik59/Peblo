"""
Tests for the local storage implementation.

Tests:
- File put/get/delete/exists
- Path traversal prevention
- Atomic rename
"""
import pytest
from app.storage.local import LocalStorage


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(str(tmp_path))


class TestLocalStorage:

    @pytest.mark.asyncio
    async def test_put_and_get(self, storage):
        await storage.put("test/file.txt", b"hello world", "text/plain")
        data = await storage.get("test/file.txt")
        assert data == b"hello world"

    @pytest.mark.asyncio
    async def test_exists(self, storage):
        assert not await storage.exists("missing.txt")
        await storage.put("exists.txt", b"data", "text/plain")
        assert await storage.exists("exists.txt")

    @pytest.mark.asyncio
    async def test_delete(self, storage):
        await storage.put("to_delete.txt", b"data", "text/plain")
        assert await storage.exists("to_delete.txt")
        result = await storage.delete("to_delete.txt")
        assert result is True
        assert not await storage.exists("to_delete.txt")

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, storage):
        result = await storage.delete("nope.txt")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, storage):
        data = await storage.get("nope.txt")
        assert data is None

    def test_path_traversal_prevention(self, storage):
        with pytest.raises(ValueError, match="Path traversal"):
            storage._resolve("../../etc/passwd")

    def test_public_url(self, storage):
        url = storage.get_public_url("artwork/test.jpg")
        assert url == "/storage/artwork/test.jpg"

    @pytest.mark.asyncio
    async def test_atomic_rename(self, storage):
        await storage.put("old.json", b'{"version": 1}', "application/json")
        result = await storage.atomic_rename("old.json", "new.json")
        assert result is True
        assert not await storage.exists("old.json")
        data = await storage.get("new.json")
        assert data == b'{"version": 1}'
