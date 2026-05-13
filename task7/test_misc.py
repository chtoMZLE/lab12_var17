"""Miscellaneous tests covering remaining uncovered lines."""

from __future__ import annotations

from httpx import AsyncClient

from app.models.user import User
from conftest import bearer

_W_BASE = {"name": "Test", "date": "2025-05-14T10:00:00Z", "exercises": []}


async def test_health_check(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_create_workout_negative_duration_rejected(client: AsyncClient, user: User) -> None:
    """WorkoutCreate.duration_positive validator: duration_minutes <= 0 must fail."""
    resp = await client.post(
        "/workouts/",
        json={**_W_BASE, "duration_minutes": -5},
        headers=bearer(user),
    )
    assert resp.status_code == 422


async def test_create_workout_zero_duration_rejected(client: AsyncClient, user: User) -> None:
    resp = await client.post(
        "/workouts/",
        json={**_W_BASE, "duration_minutes": 0},
        headers=bearer(user),
    )
    assert resp.status_code == 422


async def test_get_nonexistent_progress(client: AsyncClient, user: User) -> None:
    resp = await client.get("/progress/9999", headers=bearer(user))
    assert resp.status_code == 404


async def test_token_with_unknown_user_id(client: AsyncClient) -> None:
    """dependencies.py: user lookup returns None → 401."""
    from app.services.auth import create_access_token
    token = create_access_token(999999)
    resp = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
