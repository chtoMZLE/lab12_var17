"""
Shared pytest fixtures for the fitness platform test suite.

Execution order matters: os.environ must be populated BEFORE any app module
is imported, because `settings = Settings()` runs at module-level in config.py.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ── 1. Env vars first (settings validation happens on first import) ──────────
# DATABASE_URL must be SQLite so app's module-level engine doesn't try to
# import asyncpg (which is only needed in production with PostgreSQL).
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-exactly-32-chars!!")

# ── 2. Add task1/ to sys.path so `from app.xxx import yyy` works ─────────────
sys.path.insert(0, str(Path(__file__).parent.parent / "task1"))

# ── 3. App imports (safe after env vars are in place) ─────────────────────────
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.user import User, UserRole
import app.services.auth as _auth_svc
from app.services.auth import create_access_token, hash_password

# ── 4. Patch bcrypt → sha256_crypt for Python 3.14 + bcrypt 5.x compatibility ─
# passlib 1.7.4 is incompatible with bcrypt>=4.x (changed API). In tests we
# swap the context to sha256_crypt, which has no binary dependency. Production
# code is unaffected (Docker uses a compatible bcrypt version).
_auth_svc.pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

# ── In-memory SQLite engine shared across all tests in a session ──────────────
_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_SessionLocal = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


async def _override_get_db():
    async with _SessionLocal() as session:
        yield session


# ── Reset DB schema before/after every test for isolation ────────────────────
@pytest_asyncio.fixture(autouse=True)
async def _reset_db():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncSession:  # type: ignore[misc]
    async with _SessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncClient:  # type: ignore[misc]
    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ── User fixtures ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def user(db: AsyncSession) -> User:
    u = User(
        email="user@test.com",
        hashed_password=hash_password("password123"),
        role=UserRole.user,
        is_active=True,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest_asyncio.fixture
async def admin(db: AsyncSession) -> User:
    u = User(
        email="admin@test.com",
        hashed_password=hash_password("password123"),
        role=UserRole.admin,
        is_active=True,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest_asyncio.fixture
async def other(db: AsyncSession) -> User:
    """A second regular user — used for cross-user access tests."""
    u = User(
        email="other@test.com",
        hashed_password=hash_password("password123"),
        role=UserRole.user,
        is_active=True,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


def bearer(u: User) -> dict[str, str]:
    """Return Authorization header dict for the given user."""
    return {"Authorization": f"Bearer {create_access_token(u.id)}"}
