from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_admin, get_current_user
from app.models.exercise import Exercise
from app.models.user import User
from app.models.workout import Workout
from app.schemas.workout import WorkoutCreate, WorkoutRead, WorkoutUpdate

router = APIRouter(prefix="/workouts", tags=["workouts"])


async def _get_own_workout(workout_id: int, user_id: int, db: AsyncSession) -> Workout:
    result = await db.execute(
        select(Workout)
        .where(Workout.id == workout_id, Workout.user_id == user_id)
        .options(selectinload(Workout.exercises))
    )
    workout = result.scalar_one_or_none()
    if workout is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return workout


@router.post("/", response_model=WorkoutRead, status_code=status.HTTP_201_CREATED)
async def create_workout(
    payload: WorkoutCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Workout:
    workout = Workout(
        user_id=current_user.id,
        name=payload.name,
        date=payload.date,
        duration_minutes=payload.duration_minutes,
        notes=payload.notes,
    )
    for ex_data in payload.exercises:
        exercise = Exercise(
            name=ex_data.name,
            sets=ex_data.sets,
            reps=ex_data.reps,
            weight_kg=ex_data.weight_kg,
        )
        workout.exercises.append(exercise)
    db.add(workout)
    await db.commit()
    # Skip db.refresh: the re-fetch with selectinload below is the single source of truth.
    result = await db.execute(
        select(Workout).where(Workout.id == workout.id).options(selectinload(Workout.exercises))
    )
    return result.scalar_one()


@router.get("/", response_model=list[WorkoutRead])
async def list_workouts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[Workout]:
    result = await db.execute(
        select(Workout)
        .where(Workout.user_id == current_user.id)
        .options(selectinload(Workout.exercises))
        .order_by(Workout.date.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{workout_id}", response_model=WorkoutRead)
async def get_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Workout:
    return await _get_own_workout(workout_id, current_user.id, db)


@router.patch("/{workout_id}", response_model=WorkoutRead)
async def update_workout(
    workout_id: int,
    payload: WorkoutUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Workout:
    workout = await _get_own_workout(workout_id, current_user.id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(workout, field, value)
    await db.commit()
    result = await db.execute(
        select(Workout).where(Workout.id == workout.id).options(selectinload(Workout.exercises))
    )
    return result.scalar_one()


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    workout = await _get_own_workout(workout_id, current_user.id, db)
    await db.delete(workout)
    await db.commit()


# --- Admin endpoint ---

@router.delete("/admin/{workout_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
async def admin_delete_workout(workout_id: int, db: AsyncSession = Depends(get_db)) -> None:
    result = await db.execute(select(Workout).where(Workout.id == workout_id))
    workout = result.scalar_one_or_none()
    if workout is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    await db.delete(workout)
    await db.commit()
