from datetime import datetime

from pydantic import BaseModel, field_validator


class ExerciseCreate(BaseModel):
    name: str
    sets: int
    reps: int
    weight_kg: float | None = None

    @field_validator("sets", "reps")
    @classmethod
    def must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Must be a positive integer")
        return v

    @field_validator("weight_kg")
    @classmethod
    def weight_non_negative(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("Weight cannot be negative")
        return v


class ExerciseUpdate(BaseModel):
    name: str | None = None
    sets: int | None = None
    reps: int | None = None
    weight_kg: float | None = None


class ExerciseRead(BaseModel):
    id: int
    workout_id: int
    name: str
    sets: int
    reps: int
    weight_kg: float | None
    created_at: datetime

    model_config = {"from_attributes": True}
