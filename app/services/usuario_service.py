"""Gestión de usuarios por el Admin: alta por invitación (sin contraseña), edición y (des)activación."""
import secrets

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Cargo, Trabajador, Usuario
from app.schemas.usuario import UsuarioIn, UsuarioUpdate
from app.services.acceso_service import (
    crear_usuario_con_invitacion,
    email_en_uso,
    enviar_invitacion,
    normalizar_email,
    obtener_rol,
)
from app.services.common import commit_or_409
from app.services.trabajador_service import dar_de_baja, es_ultimo_admin


def _cargo(db: Session, nombre: str) -> Cargo:
    cargo = db.query(Cargo).filter(Cargo.nombre == nombre).first()
    if cargo is None or not cargo.activo:
        raise HTTPException(422, f"Cargo '{nombre}' no existe. Ejecuta: python -m app.db.init_db")
    return cargo


def crear_usuario(db: Session, datos: UsuarioIn) -> tuple[Usuario, bool]:
    if email_en_uso(db, datos.email):
        raise HTTPException(409, "Ya existe un usuario con ese correo")
    obtener_rol(db, datos.rol)
    cargo = _cargo(db, datos.cargo)
    trabajador = Trabajador(
        documento=datos.documento or f"SIN-DOC-{secrets.token_hex(4).upper()}",
        nombres=datos.nombres,
        apellidos=datos.apellidos,
        telefono=datos.telefono,
        cargo=cargo,
    )
    db.add(trabajador)
    usuario = crear_usuario_con_invitacion(db, trabajador, datos.email, datos.rol)
    commit_or_409(db, "Documento o correo ya registrados")
    db.refresh(usuario)
    return usuario, enviar_invitacion(usuario)


def actualizar_usuario(db: Session, usuario: Usuario, datos: UsuarioUpdate, actor: Usuario) -> Usuario:
    cambios = datos.model_dump(exclude_unset=True)
    t = usuario.trabajador

    nuevo_email = None
    if cambios.get("email") is not None:
        nuevo_email = normalizar_email(cambios["email"])
        if email_en_uso(db, nuevo_email, excluir_usuario_id=usuario.id):
            raise HTTPException(409, "Ya existe un usuario con ese correo")

    nuevo_cargo = _cargo(db, cambios["cargo"]) if cambios.get("cargo") is not None else None
    nuevo_rol = cambios.get("rol")
    if nuevo_rol is not None and nuevo_rol not in {r.nombre for r in usuario.roles}:
        if usuario.id == actor.id:
            raise HTTPException(409, "No puedes cambiar tu propio rol")
        if es_ultimo_admin(db, usuario):
            raise HTTPException(409, "No se puede quitar el rol Admin al único Admin activo")
        rol = obtener_rol(db, nuevo_rol)
    else:
        rol = None

    if nuevo_email is not None:
        usuario.email = nuevo_email

    for campo in ("nombres", "apellidos", "telefono", "documento"):
        if cambios.get(campo) is not None:
            setattr(t, campo, cambios[campo])
    if nuevo_cargo is not None:
        t.cargo = nuevo_cargo
    if rol is not None:
        usuario.roles = [rol]

    commit_or_409(db, "Documento o correo ya registrados")
    db.refresh(usuario)
    return usuario


def desactivar_usuario(
    db: Session, usuario: Usuario, actor: Usuario, reemplazo_id: int | None, sin_relevo: bool
) -> None:
    """Reutiliza la baja de personal: si está en la matriz exige reemplazo (409 EN_MATRIZ)."""
    dar_de_baja(db, usuario.trabajador, actor, reemplazo_id, sin_relevo)


def activar_usuario(db: Session, usuario: Usuario) -> Usuario:
    usuario.trabajador.activo = True
    usuario.activo = True
    db.commit()
    db.refresh(usuario)
    return usuario
