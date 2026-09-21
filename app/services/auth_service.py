"""Servicio de autenticación: verificación de credenciales y emisión de tokens."""
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, verify_password
from app.models.usuario import Usuario


def authenticate_user(db: Session, username: str, password: str) -> Usuario | None:
    """Devuelve el Usuario si las credenciales son válidas y está activo; None en caso contrario."""
    usuario = db.query(Usuario).filter(Usuario.username == username).first()
    if usuario is None or not usuario.activo:
        return None
    if not verify_password(password, usuario.password_hash):
        return None
    return usuario


def build_tokens_for_user(usuario: Usuario) -> tuple[str, str]:
    """Genera el par (access_token, refresh_token) para un usuario autenticado."""
    roles = [rol.nombre for rol in usuario.roles]
    access_token = create_access_token(subject=usuario.username, roles=roles)
    refresh_token = create_refresh_token(subject=usuario.username, roles=roles)
    return access_token, refresh_token
