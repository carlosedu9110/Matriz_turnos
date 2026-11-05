"""Acceso a cuentas: creación con invitación, recuperación y restablecimiento de contraseña.

Nadie (ni el Admin) conoce las contraseñas: las cuentas nuevas nacen con una clave aleatoria
desconocida y el usuario define la suya mediante un enlace de un solo uso enviado a su correo.
"""
import re
from datetime import timedelta

import jwt
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import (
    TOKEN_TYPE_RESET,
    create_reset_token,
    decode_token,
    generate_unusable_password_hash,
    hash_password,
    password_fingerprint,
)
from app.models import Rol, Trabajador, Usuario
from app.services import email_service

MENSAJE_RECUPERACION = "Si el correo está registrado, recibirás un enlace para restablecer tu contraseña."


def normalizar_email(email: str) -> str:
    return email.strip().lower()


def email_en_uso(db: Session, email: str, excluir_usuario_id: int | None = None) -> bool:
    q = db.query(Usuario.id).filter(Usuario.email == normalizar_email(email))
    if excluir_usuario_id is not None:
        q = q.filter(Usuario.id != excluir_usuario_id)
    return q.first() is not None


def _username_unico(db: Session, email: str) -> str:
    base = (re.sub(r"[^a-z0-9._-]", "", email.split("@")[0]) or "usuario")[:40]
    candidato, n = base, 1
    while db.query(Usuario.id).filter(Usuario.username == candidato).first():
        n += 1
        candidato = f"{base}{n}"
    return candidato


def obtener_rol(db: Session, nombre: str) -> Rol:
    rol = db.query(Rol).filter(Rol.nombre == nombre).first()
    if rol is None:
        raise HTTPException(422, f"Rol '{nombre}' no existe. Ejecuta: python -m app.db.init_db")
    return rol


def crear_usuario_con_invitacion(db: Session, trabajador: Trabajador, email: str, rol: str) -> Usuario:
    email = normalizar_email(email)
    if email_en_uso(db, email):
        raise HTTPException(409, "Ya existe un usuario con ese correo")
    usuario = Usuario(
        username=_username_unico(db, email),
        email=email,
        password_hash=generate_unusable_password_hash(),
        roles=[obtener_rol(db, rol)],
    )
    trabajador.usuario = usuario
    return usuario


def enviar_invitacion(usuario: Usuario) -> bool:
    token = create_reset_token(
        usuario.email, usuario.password_hash, timedelta(hours=settings.invite_token_expire_hours)
    )
    return email_service.send_invitation(usuario.email, usuario.nombres, token)


def solicitar_recuperacion(db: Session, email: str) -> None:
    """Envía el enlace si la cuenta existe y está activa. El resultado no se revela al solicitante."""
    usuario = db.query(Usuario).filter(Usuario.email == normalizar_email(email)).first()
    if usuario is None or not usuario.activo or not usuario.trabajador.activo:
        return
    token = create_reset_token(
        usuario.email, usuario.password_hash, timedelta(minutes=settings.reset_token_expire_minutes)
    )
    email_service.send_password_reset(usuario.email, usuario.nombres, token)


def restablecer_password(db: Session, token: str, nueva: str) -> None:
    invalido = HTTPException(400, "El enlace no es válido o ya venció. Solicita uno nuevo.")
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as exc:
        raise invalido from exc
    if payload.get("type") != TOKEN_TYPE_RESET or not payload.get("sub"):
        raise invalido
    usuario = db.query(Usuario).filter(Usuario.email == payload["sub"]).first()
    if usuario is None or not usuario.activo or not usuario.trabajador.activo:
        raise invalido
    # Un solo uso: tras cambiar la contraseña la huella cambia y el enlace deja de servir.
    if payload.get("pwf") != password_fingerprint(usuario.password_hash):
        raise invalido
    usuario.password_hash = hash_password(nueva)
    db.commit()
