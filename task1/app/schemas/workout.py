from datetime import datetime

from pydantic import BaseModel, field_validator

from app.schemas.exercise import ExerciseCreate, ExerciseRead


class WorkoutCreate(BaseModel):
    name: str
    date: datetime
    duration_minutes: int | None = None
    notes: str | None = None
    exercises: list[ExerciseCreate] = []

    @field_validator("duration_minutes")
    @classmethod
    def duration_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Duration must be positive")
        return v


class WorkoutUpdate(BaseModel):
    name: str | None = None
    date: datetime | None = None
    duration_minutes: int | None = None
    notes: str | None = None


class WorkoutRead(BaseModel):
    id: int
    user_id: int
    name: str
    date: datetime
    duration_minutes: int | None
    notes: str | None
    created_at: datetime
    exercises: list[ExerciseRead] = []

    model_config = {"from_attributes": True}
