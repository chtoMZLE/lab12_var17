"""Tests for /progress endpoints.

Edge cases covered:
- Negative max_weight_kg must be rejected
- Negative / zero total_reps must be rejected
- Accessing another user's progress record must return 404
"""

from __future__ import annotations

from httpx import AsyncClient

from app.models.user import User
from conftest import bearer

_P = {
    "exercise_name": "Deadlift",
    "max_weight_kg": 150.0,
    "total_reps": 5,
    "recorded_at": "2025-05-14T10:00:00Z",
}


# ── Create ────────────────────────────────────────────────────────────────────

async def test_create_progress_valid(client: AsyncClient, user: User) -> None:
    resp = await client.post("/progress/", json=_P, headers=bearer(user))
    assert resp.status_code == 201
    data = resp.json()
    assert data["exercise_name"] == "Deadlift"
    assert data["user_id"] == user.id


async def test_create_progress_negative_weight_rejected(client: AsyncClient, user: User) -> None:
    """Edge case: negative max_weight_kg must fail schema validation."""
    resp = await client.post("/progress/", json={**_P, "max_weight_kg": -1.0}, headers=bearer(user))
    assert resp.status_code == 422


async def test_create_progress_negative_reps_rejected(client: AsyncClient, user: User) -> None:
    """Edge case: total_reps must be positive."""
    resp = await client.post("/progress/", json={**_P, "total_reps": -3}, headers=bearer(user))
    assert resp.status_code == 422


async def test_create_progress_zero_reps_rejected(client: AsyncClient, user: User) -> None:
    resp = await client.post("/progress/", json={**_P, "total_reps": 0}, headers=bearer(user))
    assert resp.status_code == 422


async def test_create_progress_null_weight_allowed(client: AsyncClient, user: User) -> None:
    """max_weight_kg is optional — null is valid (e.g., tracking reps only)."""
    resp = await client.post("/progress/", json={**_P, "max_weight_kg": None}, headers=bearer(user))
    assert resp.status_code == 201
    assert resp.json()["max_weight_kg"] is None


# ── List ──────────────────────────────────────────────────────────────────────

async def test_list_progress_returns_only_own(client: AsyncClient, user: User, other: User) -> None:
    await client.post("/progress/", json=_P, headers=bearer(user))
    await client.post("/progress/", json=_P, headers=bearer(other))
    resp = await client.get("/progress/", headers=bearer(user))
    assert resp.status_code == 200
    assert all(r["user_id"] == user.id for r in resp.json())


async def test_list_progress_pagination(client: AsyncClient, user: User) -> None:
    for _ in range(5):
        await client.post("/progress/", json=_P, headers=bearer(user))
    resp = await client.get("/progress/?skip=1&limit=2", headers=bearer(user))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── Get ───────────────────────────────────────────────────────────────────────

async def test_get_own_progress(client: AsyncClient, user: User) -> None:
    rid = (await client.post("/progress/", json=_P, headers=bearer(user))).json()["id"]
    resp = await client.get(f"/progress/{rid}", headers=bearer(user))
    assert resp.status_code == 200


async def test_get_other_user_progress_returns_404(client: AsyncClient, user: User, other: User) -> None:
    """Edge case: users must not read each other's progress records."""
    rid = (await client.post("/progress/", json=_P, headers=bearer(user))).json()["id"]
    resp = await client.get(f"/progress/{rid}", headers=bearer(other))
    assert resp.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

async def test_update_own_progress(client: AsyncClient, user: User) -> None:
    rid = (await client.post("/progress/", json=_P, headers=bearer(user))).json()["id"]
    resp = await client.patch(f"/progress/{rid}", json={"max_weight_kg": 160.0}, headers=bearer(user))
    assert resp.status_code == 200
    assert resp.json()["max_weight_kg"] == 160.0


async def test_update_other_user_progress_returns_404(client: AsyncClient, user: User, other: User) -> None:
    rid = (await client.post("/progress/", json=_P, headers=bearer(user))).json()["id"]
    resp = await client.patch(f"/progress/{rid}", json={"max_weight_kg": 200.0}, headers=bearer(other))
    assert resp.status_code == 404


async def test_update_nonexistent_progress(client: AsyncClient, user: User) -> None:
    resp = await client.patch("/progress/9999", json={"max_weight_kg": 100.0}, headers=bearer(user))
    assert resp.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

async def test_delete_own_progress(client: AsyncClient, user: User) -> None:
    rid = (await client.post("/progress/", json=_P, headers=bearer(user))).json()["id"]
    resp = await client.delete(f"/progress/{rid}", headers=bearer(user))
    assert resp.status_code == 204


async def test_delete_other_user_progress_returns_404(client: AsyncClient, user: User, other: User) -> None:
    rid = (await client.post("/progress/", json=_P, headers=bearer(user))).json()["id"]
    resp = await client.delete(f"/progress/{rid}", headers=bearer(other))
    assert resp.status_code == 404


async def test_delete_nonexistent_progress(client: AsyncClient, user: User) -> None:
    resp = await client.delete("/progress/9999", headers=bearer(user))
    assert resp.status_code == 404


# ── Admin ─────────────────────────────────────────────────────────────────────

async def test_admin_can_delete_any_progress(client: AsyncClient, user: User, admin: User) -> None:
    rid = (await client.post("/progress/", json=_P, headers=bearer(user))).json()["id"]
    resp = await client.delete(f"/progress/admin/{rid}", headers=bearer(admin))
    assert resp.status_code == 204


async def test_admin_delete_nonexistent_progress(client: AsyncClient, admin: User) -> None:
    resp = await client.delete("/progress/admin/9999", headers=bearer(admin))
    assert resp.status_code == 404


async def test_non_admin_cannot_use_admin_delete(client: AsyncClient, user: User, other: User) -> None:
    rid = (await client.post("/progress/", json=_P, headers=bearer(user))).json()["id"]
    resp = await client.delete(f"/progress/admin/{rid}", headers=bearer(other))
    assert resp.status_code == 403
