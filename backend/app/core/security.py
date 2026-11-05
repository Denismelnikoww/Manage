"""Хеширование паролей и работа с JWT (WBS 4.1.2)."""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# bcrypt принимает пароль не длиннее 72 байт
BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """Возвращает bcrypt-хеш пароля (соль генерируется автоматически)."""
    return bcrypt.hashpw(
        password.encode("utf-8")[:BCRYPT_MAX_BYTES], bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет пароль. Сравнение выполняет bcrypt (constant-time)."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:BCRYPT_MAX_BYTES],
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> tuple[str, int]:
    """Создаёт JWT. Возвращает (токен, время жизни в секундах)."""
    now = datetime.now(timezone.utc)
    lifetime = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + lifetime,
        "type": "access",
    }
    if extra:
        payload.update(extra)

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, int(lifetime.total_seconds())


def decode_token(token: str) -> dict[str, Any]:
    """Декодирует JWT. Бросает jose.JWTError при невалидном токене."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


__all__ = [
    "JWTError",
    "create_access_token",
    "decode_token",
    "hash_password",
    "verify_password",
]