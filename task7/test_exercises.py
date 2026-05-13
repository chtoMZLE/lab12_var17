"""Tests for /workouts/{id}/exercises endpoints.

Edge cases covered:
- Negative weight must be rejected (Pydantic validator)
- Zero sets/reps must be rejected
- Creating exercise on a workout owned by another user
"""

from __future__ import annotations

from httpx import AsyncClient

from app.models.user import User
from conftest import bearer

_WORKOUT = {"name": "Strength", "date": "2025-05-14T10:00:00Z", "exercises": []}
_EX = {"name": "Bench Press", "sets": 4, "reps": 8, "weight_kg": 80.0}


async def _make_workout(client: AsyncClient, user: User) -> int:
    resp = await client.post("/workouts/", json=_WORKOUT, headers=bearer(user))
    return resp.json()["id"]


# ── Create ────────────────────────────────────────────────────────────────────

async def test_create_exercise_valid(client: AsyncClient, user: User) -> None:
    wid = await _make_workout(client, user)
    resp = await client.post(f"/workouts/{wid}/exercises/", json=_EX, headers=bearer(user))
    assert resp.status_code == 201
    assert resp.json()["weight_kg"] == 80.0
    assert resp.json()["workout_id"] == wid


async def test_create_exercise_negative_weight_rejected(client: AsyncClient, user: User) -> None:
    """Edge case: negative weight_kg must be rejected by Pydantic validator."""
    wid = await _make_workout(client, user)
    resp = await client.post(f"/workouts/{wid}/exercises/", json={**_EX, "weight_kg": -10.0}, headers=bearer(user))
    assert resp.status_code == 422


async def test_create_exercise_zero_sets_rejected(client: AsyncClient, user: User) -> None:
    """Edge case: sets=0 is not positive — must be rejected."""
    wid = await _make_workout(client, user)
    resp = await client.post(f"/workouts/{wid}/exercises/", json={**_EX, "sets": 0}, headers=bearer(user))
    assert resp.status_code == 422


async def test_create_exercise_zero_reps_rejected(client: AsyncClient, user: User) -> None:
    wid = await _make_workout(client, user)
    resp = await client.post(f"/workouts/{wid}/exercises/", json={**_EX, "reps": 0}, headers=bearer(user))
    assert resp.status_code == 422


async def test_create_exercise_null_weight_allowed(client: AsyncClient, user: User) -> None:
    """weight_kg is optional — None/null is a valid value (bodyweight exercise)."""
    wid = await _make_workout(client, user)
    payload = {**_EX, "weight_kg": None}
    resp = await client.post(f"/workouts/{wid}/exercises/", json=payload, headers=bearer(user))
    assert resp.status_code == 201
    assert resp.json()["weight_kg"] is None


async def test_create_exercise_on_nonexistent_workout(client: AsyncClient, user: User) -> None:
    resp = await client.post("/workouts/9999/exercises/", json=_EX, headers=bearer(user))
    assert resp.status_code == 404


async def test_create_exercise_on_other_users_workout(client: AsyncClient, user: User, other: User) -> None:
    wid = await _make_workout(client, user)
    resp = await client.post(f"/workouts/{wid}/exercises/", json=_EX, headers=bearer(other))
    assert resp.status_code == 404


# ── List ──────────────────────────────────────────────────────────────────────

async def test_list_exercises(client: AsyncClient, user: User) -> None:
    wid = await _make_workout(client, user)
    await client.post(f"/workouts/{wid}/exercises/", json=_EX, headers=bearer(user))
    await client.post(f"/workouts/{wid}/exercises/", json={**_EX, "name": "Squat"}, headers=bearer(user))
    resp = await client.get(f"/workouts/{wid}/exercises/", headers=bearer(user))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_exercises_pagination(client: AsyncClient, user: User) -> None:
    wid = await _make_workout(client, user)
    for i in range(5):
        await client.post(f"/workouts/{wid}/exercises/", json={**_EX, "name": f"Ex {i}"}, headers=bearer(user))
    resp = await client.get(f"/workouts/{wid}/exercises/?skip=1&limit=2", headers=bearer(user))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── Update ────────────────────────────────────────────────────────────────────

async def test_update_exercise(client: AsyncClient, user: User) -> None:
    wid = await _make_workout(client, user)
    eid = (await client.post(f"/workouts/{wid}/exercises/", json=_EX, headers=bearer(user))).json()["id"]
    resp = await client.patch(f"/workouts/{wid}/exercises/{eid}", json={"weight_kg": 90.0}, headers=bearer(user))
    assert resp.status_code == 200
    assert resp.json()["weight_kg"] == 90.0


async def test_update_nonexistent_exercise(client: AsyncClient, user: User) -> None:
    wid = await _make_workout(client, user)
    resp = await client.patch(f"/workouts/{wid}/exercises/9999", json={"weight_kg": 90.0}, headers=bearer(user))
    assert resp.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

async def test_delete_exercise(client: AsyncClient, user: User) -> None:
    wid = await _make_workout(client, user)
    eid = (await client.post(f"/workouts/{wid}/exercises/", json=_EX, headers=bearer(user))).json()["id"]
    resp = await client.delete(f"/workouts/{wid}/exercises/{eid}", headers=bearer(user))
    assert resp.status_code == 204


async def test_delete_nonexistent_exercise(client: AsyncClient, user: User) -> None:
    wid = await _make_workout(client, user)
    resp = await client.delete(f"/workouts/{wid}/exercises/9999", headers=bearer(user))
    assert resp.status_code == 404
