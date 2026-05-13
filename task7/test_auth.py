"""Tests for /auth endpoints: register, login, token validation."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from conftest import bearer


# ── Registration ──────────────────────────────────────────────────────────────

async def test_register_success(client: AsyncClient) -> None:
    resp = await client.post("/auth/register", json={"email": "new@test.com", "password": "password123"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@test.com"
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert "hashed_password" not in data


async def test_register_duplicate_email(client: AsyncClient, user: User) -> None:
    resp = await client.post("/auth/register", json={"email": "user@test.com", "password": "password123"})
    assert resp.status_code == 409


async def test_register_weak_password_rejected(client: AsyncClient) -> None:
    """Password shorter than 8 chars must be rejected by Pydantic validator."""
    resp = await client.post("/auth/register", json={"email": "weak@test.com", "password": "short"})
    assert resp.status_code == 422


async def test_register_invalid_email_rejected(client: AsyncClient) -> None:
    resp = await client.post("/auth/register", json={"email": "not-an-email", "password": "password123"})
    assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

async def test_login_success(client: AsyncClient, user: User) -> None:
    resp = await client.post("/auth/login", data={"username": "user@test.com", "password": "password123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient, user: User) -> None:
    resp = await client.post("/auth/login", data={"username": "user@test.com", "password": "wrongpassword"})
    assert resp.status_code == 401


async def test_login_nonexistent_user(client: AsyncClient) -> None:
    resp = await client.post("/auth/login", data={"username": "nobody@test.com", "password": "password123"})
    assert resp.status_code == 401


async def test_login_inactive_user(client: AsyncClient, db: AsyncSession, user: User) -> None:
    user.is_active = False
    await db.commit()
    resp = await client.post("/auth/login", data={"username": "user@test.com", "password": "password123"})
    assert resp.status_code == 403


# ── Token / protected endpoint ────────────────────────────────────────────────

async def test_protected_endpoint_without_token(client: AsyncClient) -> None:
    resp = await client.get("/users/me")
    assert resp.status_code == 401


async def test_protected_endpoint_with_invalid_token(client: AsyncClient) -> None:
    resp = await client.get("/users/me", headers={"Authorization": "Bearer totally.invalid.token"})
    assert resp.status_code == 401


async def test_protected_endpoint_with_malformed_header(client: AsyncClient) -> None:
    resp = await client.get("/users/me", headers={"Authorization": "NotBearer sometoken"})
    assert resp.status_code == 401
