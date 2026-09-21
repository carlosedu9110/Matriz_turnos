"""Dependencias de FastAPI para autenticación y autorización basada en roles."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.core.security import TOKEN_TYPE_ACCESS, decode_token
from app.db.session import get_db
from app.models.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudo validar las credenciales",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Resuelve el usuario autenticado a partir del JWT de acceso enviado en el header Authorization."""
    if token is None:
        raise CREDENTIALS_EXCEPTION
    try:
        payload = decode_token(token)
    except PyJWTError as exc:
        raise CREDENTIALS_EXCEPTION from exc

    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise CREDENTIALS_EXCEPTION

    username = payload.get("sub")
    if username is None:
        raise CREDENTIALS_EXCEPTION

    usuario = db.query(Usuario).filter(Usuario.username == username).first()
    if usuario is None or not usuario.activo:
        raise CREDENTIALS_EXCEPTION
    return usuario


def get_current_active_user(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """Asegura que el usuario autenticado esté activo (redundante con get_current_user, explícito por claridad)."""
    if not current_user.activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")
    return current_user


def require_roles(*allowed_roles: str):
    """Fábrica de dependencia que exige que el usuario tenga al menos uno de los roles indicados."""

    def _checker(current_user: Usuario = Depends(get_current_active_user)) -> Usuario:
        user_roles = {rol.nombre for rol in current_user.roles}
        if not user_roles.intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos suficientes para esta acción",
            )
        return current_user

    return _checker
