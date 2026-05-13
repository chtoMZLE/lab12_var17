"""Tests for /users endpoints: profile management and admin operations."""

from __future__ import annotations

from httpx import AsyncClient

from app.models.user import User
from conftest import bearer


async def test_get_me(client: AsyncClient, user: User) -> None:
    resp = await client.get("/users/me", headers=bearer(user))
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@test.com"


async def test_update_me_email(client: AsyncClient, user: User) -> None:
    resp = await client.patch("/users/me", json={"email": "updated@test.com"}, headers=bearer(user))
    assert resp.status_code == 200
    assert resp.json()["email"] == "updated@test.com"


async def test_update_me_duplicate_email_rejected(client: AsyncClient, user: User, other: User) -> None:
    """Cannot steal another user's email address."""
    resp = await client.patch("/users/me", json={"email": "other@test.com"}, headers=bearer(user))
    assert resp.status_code == 409


async def test_update_me_no_changes(client: AsyncClient, user: User) -> None:
    """Sending empty patch body is a no-op and must succeed."""
    resp = await client.patch("/users/me", json={}, headers=bearer(user))
    assert resp.status_code == 200


# ── Admin endpoints ───────────────────────────────────────────────────────────

async def test_list_users_as_admin(client: AsyncClient, admin: User, user: User, other: User) -> None:
    resp = await client.get("/users/", headers=bearer(admin))
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert "user@test.com" in emails
    assert "other@test.com" in emails


async def test_list_users_as_regular_user_forbidden(client: AsyncClient, user: User) -> None:
    resp = await client.get("/users/", headers=bearer(user))
    assert resp.status_code == 403


async def test_list_users_pagination(client: AsyncClient, admin: User, user: User, other: User) -> None:
    resp = await client.get("/users/?skip=0&limit=1", headers=bearer(admin))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_delete_user_as_admin(client: AsyncClient, admin: User, user: User) -> None:
    resp = await client.delete(f"/users/{user.id}", headers=bearer(admin))
    assert resp.status_code == 204


async def test_delete_nonexistent_user_as_admin(client: AsyncClient, admin: User) -> None:
    resp = await client.delete("/users/9999", headers=bearer(admin))
    assert resp.status_code == 404


async def test_delete_user_as_regular_user_forbidden(client: AsyncClient, user: User, other: User) -> None:
    resp = await client.delete(f"/users/{other.id}", headers=bearer(user))
    assert resp.status_code == 403
