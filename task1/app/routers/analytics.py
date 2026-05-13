from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.exercise import Exercise
from app.models.user import User
from app.models.workout import Workout
from app.schemas.progress import WeeklyAnalytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/weekly", response_model=WeeklyAnalytics)
async def get_weekly_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WeeklyAnalytics:
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)

    count_result = await db.execute(
        select(func.count(Workout.id)).where(
            Workout.user_id == current_user.id,
            Workout.date >= week_start,
        )
    )
    workout_count: int = count_result.scalar_one() or 0

    weight_result = await db.execute(
        select(func.coalesce(func.sum(Exercise.weight_kg * Exercise.sets * Exercise.reps), 0.0))
        .join(Workout, Exercise.workout_id == Workout.id)
        .where(
            Workout.user_id == current_user.id,
            Workout.date >= week_start,
            Exercise.weight_kg.isnot(None),
        )
    )
    total_weight: float = float(weight_result.scalar_one() or 0.0)

    return WeeklyAnalytics(
        workout_count=workout_count,
        total_weight_lifted_kg=total_weight,
        week_start=week_start,
        week_end=now,
    )
