from datetime import datetime

from pydantic import BaseModel, field_validator


class ProgressCreate(BaseModel):
    exercise_name: str
    max_weight_kg: float | None = None
    total_reps: int | None = None
    recorded_at: datetime

    @field_validator("max_weight_kg")
    @classmethod
    def weight_non_negative(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("Weight cannot be negative")
        return v

    @field_validator("total_reps")
    @classmethod
    def reps_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Total reps must be positive")
        return v


class ProgressUpdate(BaseModel):
    max_weight_kg: float | None = None
    total_reps: int | None = None
    recorded_at: datetime | None = None


class ProgressRead(BaseModel):
    id: int
    user_id: int
    exercise_name: str
    max_weight_kg: float | None
    total_reps: int | None
    recorded_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class WeeklyAnalytics(BaseModel):
    workout_count: int
    total_weight_lifted_kg: float
    week_start: datetime
    week_end: datetime
