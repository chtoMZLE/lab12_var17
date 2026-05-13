"""Tests for /analytics/weekly endpoint."""

from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient

from app.models.user import User
from conftest import bearer


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_WORKOUT_WITH_WEIGHT = {
    "name": "Analytics Test",
    "date": _now(),  # within the 7-day window
    "exercises": [
        {"name": "Squat", "sets": 3, "reps": 10, "weight_kg": 50.0},
    ],
}

_WORKOUT_NO_WEIGHT = {
    "name": "Bodyweight",
    "date": _now(),
    "exercises": [
        {"name": "Pull-up", "sets": 3, "reps": 10, "weight_kg": None},
    ],
}


async def test_weekly_analytics_no_workouts(client: AsyncClient, user: User) -> None:
    resp = await client.get("/analytics/weekly", headers=bearer(user))
    assert resp.status_code == 200
    data = resp.json()
    assert data["workout_count"] == 0
    assert data["total_weight_lifted_kg"] == 0.0
    assert "week_start" in data
    assert "week_end" in data


async def test_weekly_analytics_counts_workouts_and_weight(client: AsyncClient, user: User) -> None:
    await client.post("/workouts/", json=_WORKOUT_WITH_WEIGHT, headers=bearer(user))
    await client.post("/workouts/", json=_WORKOUT_WITH_WEIGHT, headers=bearer(user))
    resp = await client.get("/analytics/weekly", headers=bearer(user))
    assert resp.status_code == 200
    data = resp.json()
    assert data["workout_count"] == 2
    # 3 sets × 10 reps × 50 kg × 2 workouts = 3 000 kg
    assert data["total_weight_lifted_kg"] == 3000.0


async def test_weekly_analytics_bodyweight_exercises_count_zero_weight(
    client: AsyncClient, user: User
) -> None:
    await client.post("/workouts/", json=_WORKOUT_NO_WEIGHT, headers=bearer(user))
    resp = await client.get("/analytics/weekly", headers=bearer(user))
    assert resp.status_code == 200
    data = resp.json()
    assert data["workout_count"] == 1
    assert data["total_weight_lifted_kg"] == 0.0


async def test_weekly_analytics_only_shows_own_data(
    client: AsyncClient, user: User, other: User
) -> None:
    """Analytics must be scoped to the authenticated user only."""
    await client.post("/workouts/", json=_WORKOUT_WITH_WEIGHT, headers=bearer(other))
    resp = await client.get("/analytics/weekly", headers=bearer(user))
    assert resp.json()["workout_count"] == 0


async def test_weekly_analytics_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/analytics/weekly")
    assert resp.status_code == 401
