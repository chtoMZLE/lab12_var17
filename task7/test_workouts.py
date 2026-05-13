"""Tests for /workouts endpoints.

Edge cases covered:
- Creating a workout with an empty exercise list (must succeed)
- Accessing another user's workout (must return 404)
"""

from __future__ import annotations

from httpx import AsyncClient

from app.models.user import User
from conftest import bearer

_W = {
    "name": "Morning Run",
    "date": "2025-05-14T08:00:00Z",
    "duration_minutes": 45,
    "notes": "Easy pace",
    "exercises": [{"name": "Push-up", "sets": 3, "reps": 15, "weight_kg": 0.0}],
}


# ── Create ────────────────────────────────────────────────────────────────────

async def test_create_workout_with_exercises(client: AsyncClient, user: User) -> None:
    resp = await client.post("/workouts/", json=_W, headers=bearer(user))
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Morning Run"
    assert len(data["exercises"]) == 1
    assert data["user_id"] == user.id


async def test_create_workout_empty_exercises(client: AsyncClient, user: User) -> None:
    """Edge case: a workout with zero exercises is valid."""
    payload = {**_W, "exercises": []}
    resp = await client.post("/workouts/", json=payload, headers=bearer(user))
    assert resp.status_code == 201
    assert resp.json()["exercises"] == []


async def test_create_workout_without_auth(client: AsyncClient) -> None:
    resp = await client.post("/workouts/", json=_W)
    assert resp.status_code == 401


# ── List ──────────────────────────────────────────────────────────────────────

async def test_list_workouts_returns_only_own(client: AsyncClient, user: User, other: User) -> None:
    await client.post("/workouts/", json=_W, headers=bearer(user))
    await client.post("/workouts/", json=_W, headers=bearer(other))
    resp = await client.get("/workouts/", headers=bearer(user))
    assert resp.status_code == 200
    ids = [w["user_id"] for w in resp.json()]
    assert all(uid == user.id for uid in ids)


async def test_list_workouts_pagination(client: AsyncClient, user: User) -> None:
    for i in range(5):
        await client.post("/workouts/", json={**_W, "name": f"Workout {i}"}, headers=bearer(user))
    resp = await client.get("/workouts/?skip=2&limit=2", headers=bearer(user))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── Get ───────────────────────────────────────────────────────────────────────

async def test_get_own_workout(client: AsyncClient, user: User) -> None:
    wid = (await client.post("/workouts/", json=_W, headers=bearer(user))).json()["id"]
    resp = await client.get(f"/workouts/{wid}", headers=bearer(user))
    assert resp.status_code == 200


async def test_get_other_user_workout_returns_404(client: AsyncClient, user: User, other: User) -> None:
    """Edge case: users must not read each other's workouts."""
    wid = (await client.post("/workouts/", json=_W, headers=bearer(user))).json()["id"]
    resp = await client.get(f"/workouts/{wid}", headers=bearer(other))
    assert resp.status_code == 404


async def test_get_nonexistent_workout(client: AsyncClient, user: User) -> None:
    resp = await client.get("/workouts/9999", headers=bearer(user))
    assert resp.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

async def test_update_own_workout(client: AsyncClient, user: User) -> None:
    wid = (await client.post("/workouts/", json=_W, headers=bearer(user))).json()["id"]
    resp = await client.patch(f"/workouts/{wid}", json={"name": "Updated"}, headers=bearer(user))
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"


async def test_update_other_user_workout_returns_404(client: AsyncClient, user: User, other: User) -> None:
    wid = (await client.post("/workouts/", json=_W, headers=bearer(user))).json()["id"]
    resp = await client.patch(f"/workouts/{wid}", json={"name": "Steal"}, headers=bearer(other))
    assert resp.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

async def test_delete_own_workout(client: AsyncClient, user: User) -> None:
    wid = (await client.post("/workouts/", json=_W, headers=bearer(user))).json()["id"]
    resp = await client.delete(f"/workouts/{wid}", headers=bearer(user))
    assert resp.status_code == 204
    # Confirm it's gone
    assert (await client.get(f"/workouts/{wid}", headers=bearer(user))).status_code == 404


async def test_delete_other_user_workout_returns_404(client: AsyncClient, user: User, other: User) -> None:
    wid = (await client.post("/workouts/", json=_W, headers=bearer(user))).json()["id"]
    resp = await client.delete(f"/workouts/{wid}", headers=bearer(other))
    assert resp.status_code == 404


# ── Admin ─────────────────────────────────────────────────────────────────────

async def test_admin_can_delete_any_workout(client: AsyncClient, user: User, admin: User) -> None:
    wid = (await client.post("/workouts/", json=_W, headers=bearer(user))).json()["id"]
    resp = await client.delete(f"/workouts/admin/{wid}", headers=bearer(admin))
    assert resp.status_code == 204


async def test_admin_delete_nonexistent_workout(client: AsyncClient, admin: User) -> None:
    resp = await client.delete("/workouts/admin/9999", headers=bearer(admin))
    assert resp.status_code == 404


async def test_non_admin_cannot_use_admin_delete(client: AsyncClient, user: User, other: User) -> None:
    wid = (await client.post("/workouts/", json=_W, headers=bearer(user))).json()["id"]
    resp = await client.delete(f"/workouts/admin/{wid}", headers=bearer(other))
    assert resp.status_code == 403
