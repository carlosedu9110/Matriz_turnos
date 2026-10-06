"""Utilidades de seguridad: hashing de contraseñas y manejo de JWT."""
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def hash_password(password: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash."""
    return pwd_context.verify(plain_password, password_hash)


def _create_token(subject: str, roles: list[str], expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "roles": roles,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, roles: list[str]) -> str:
    """Crea un JWT de acceso de corta duración."""
    return _create_token(
        subject,
        roles,
        timedelta(minutes=settings.access_token_expire_minutes),
        TOKEN_TYPE_ACCESS,
    )


def create_refresh_token(subject: str, roles: list[str]) -> str:
    """Crea un JWT de refresco de larga duración."""
    return _create_token(
        subject,
        roles,
        timedelta(days=settings.refresh_token_expire_days),
        TOKEN_TYPE_REFRESH,
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decodifica y valida un JWT. Lanza jwt.PyJWTError si es inválido o expiró."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
