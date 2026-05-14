from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.schemas.user import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Computed once at startup — reused in every login to avoid ~100ms bcrypt cost per request.
# Falls back to "" if bcrypt unavailable (test env); conftest.py regenerates it.
try:
    _DUMMY_HASH: str = pwd_context.hash("timing-attack-prevention-dummy")
except Exception:
    _DUMMY_HASH = ""


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise JWTError("Missing subject")
        return TokenData(user_id=int(user_id_str))
    except (JWTError, ValueError) as exc:
        raise ValueError("Invalid token") from exc
