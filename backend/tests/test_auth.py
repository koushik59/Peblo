"""
Unit and integration tests for Authentication and Authorization.

Tests:
- Password hashing and verification
- JWT token issuance and decoding
- Role-based access control (editor vs admin)
- Server-side authorization enforcement on protected routes
"""
import uuid
import pytest
from datetime import datetime, timezone
from fastapi import HTTPException
from app.auth.dependencies import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    require_role,
)
from app.models.user import User


class TestAuthUtils:

    def test_password_hashing(self):
        plain = "supersecret123"
        hashed = hash_password(plain)
        assert hashed != plain
        assert verify_password(plain, hashed) is True
        assert verify_password("wrongpassword", hashed) is False

    def test_jwt_token_generation_and_decoding(self):
        user_id = str(uuid.uuid4())
        token = create_access_token(
            user_id=user_id,
            email="admin@example.com",
            role="admin",
            name="Admin User",
        )
        assert isinstance(token, str)
        payload = decode_token(token)
        assert payload["sub"] == user_id
        assert payload["email"] == "admin@example.com"
        assert payload["role"] == "admin"
        assert payload["name"] == "Admin User"
        assert "exp" in payload

    def test_invalid_jwt_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid.token.here")
        assert exc_info.value.status_code == 401


class TestRoleHierarchy:

    @pytest.mark.asyncio
    async def test_admin_role_satisfies_editor_requirement(self):
        admin_user = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            role="admin",
            name="Admin",
            hashed_password="hash",
        )
        checker = require_role("editor")
        user = await checker(admin_user)
        assert user == admin_user

    @pytest.mark.asyncio
    async def test_admin_role_satisfies_admin_requirement(self):
        admin_user = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            role="admin",
            name="Admin",
            hashed_password="hash",
        )
        checker = require_role("admin")
        user = await checker(admin_user)
        assert user == admin_user

    @pytest.mark.asyncio
    async def test_editor_role_satisfies_editor_requirement(self):
        editor_user = User(
            id=uuid.uuid4(),
            email="editor@example.com",
            role="editor",
            name="Editor",
            hashed_password="hash",
        )
        checker = require_role("editor")
        user = await checker(editor_user)
        assert user == editor_user

    @pytest.mark.asyncio
    async def test_editor_role_rejected_on_admin_requirement(self):
        editor_user = User(
            id=uuid.uuid4(),
            email="editor@example.com",
            role="editor",
            name="Editor",
            hashed_password="hash",
        )
        checker = require_role("admin")
        with pytest.raises(HTTPException) as exc_info:
            await checker(editor_user)
        assert exc_info.value.status_code == 403
        assert "requires 'admin' role" in exc_info.value.detail
