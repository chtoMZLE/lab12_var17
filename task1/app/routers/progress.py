from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin, get_current_user
from app.models.progress import Progress
from app.models.user import User
from app.schemas.progress import ProgressCreate, ProgressRead, ProgressUpdate

router = APIRouter(prefix="/progress", tags=["progress"])


@router.post("/", response_model=ProgressRead, status_code=status.HTTP_201_CREATED)
async def create_progress(
    payload: ProgressCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Progress:
    record = Progress(user_id=current_user.id, **payload.model_dump())
    db.add(record)
    try:
        await db.commit()
        await db.refresh(record)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid data: constraint violation")
    return record


@router.get("/", response_model=list[ProgressRead])
async def list_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[Progress]:
    result = await db.execute(
        select(Progress)
        .where(Progress.user_id == current_user.id)
        .order_by(Progress.recorded_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{record_id}", response_model=ProgressRead)
async def get_progress(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Progress:
    result = await db.execute(
        select(Progress).where(Progress.id == record_id, Progress.user_id == current_user.id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Progress record not found")
    return record


@router.patch("/{record_id}", response_model=ProgressRead)
async def update_progress(
    record_id: int,
    payload: ProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Progress:
    result = await db.execute(
        select(Progress).where(Progress.id == record_id, Progress.user_id == current_user.id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Progress record not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_progress(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Progress).where(Progress.id == record_id, Progress.user_id == current_user.id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Progress record not found")
    await db.delete(record)
    await db.commit()


# --- Admin endpoint ---

@router.delete("/admin/{record_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
async def admin_delete_progress(record_id: int, db: AsyncSession = Depends(get_db)) -> None:
    result = await db.execute(select(Progress).where(Progress.id == record_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Progress record not found")
    await db.delete(record)
    await db.commit()
