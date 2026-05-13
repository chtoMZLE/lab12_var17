from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.exercise import Exercise
from app.models.user import User
from app.models.workout import Workout
from app.schemas.exercise import ExerciseCreate, ExerciseRead, ExerciseUpdate

router = APIRouter(prefix="/workouts/{workout_id}/exercises", tags=["exercises"])


async def _verify_workout_owner(workout_id: int, user_id: int, db: AsyncSession) -> Workout:
    result = await db.execute(select(Workout).where(Workout.id == workout_id, Workout.user_id == user_id))
    workout = result.scalar_one_or_none()
    if workout is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return workout


@router.post("/", response_model=ExerciseRead, status_code=status.HTTP_201_CREATED)
async def create_exercise(
    workout_id: int,
    payload: ExerciseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Exercise:
    await _verify_workout_owner(workout_id, current_user.id, db)
    exercise = Exercise(workout_id=workout_id, **payload.model_dump())
    db.add(exercise)
    await db.commit()
    await db.refresh(exercise)
    return exercise


@router.get("/", response_model=list[ExerciseRead])
async def list_exercises(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Exercise]:
    await _verify_workout_owner(workout_id, current_user.id, db)
    result = await db.execute(select(Exercise).where(Exercise.workout_id == workout_id))
    return list(result.scalars().all())


@router.patch("/{exercise_id}", response_model=ExerciseRead)
async def update_exercise(
    workout_id: int,
    exercise_id: int,
    payload: ExerciseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Exercise:
    await _verify_workout_owner(workout_id, current_user.id, db)
    result = await db.execute(
        select(Exercise).where(Exercise.id == exercise_id, Exercise.workout_id == workout_id)
    )
    exercise = result.scalar_one_or_none()
    if exercise is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(exercise, field, value)
    await db.commit()
    await db.refresh(exercise)
    return exercise


@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise(
    workout_id: int,
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _verify_workout_owner(workout_id, current_user.id, db)
    result = await db.execute(
        select(Exercise).where(Exercise.id == exercise_id, Exercise.workout_id == workout_id)
    )
    exercise = result.scalar_one_or_none()
    if exercise is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    await db.delete(exercise)
    await db.commit()
