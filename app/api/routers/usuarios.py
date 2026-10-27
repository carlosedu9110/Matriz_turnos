"""Gestión de usuarios: exclusiva del rol Admin.

El Admin nunca define ni ve contraseñas: cada usuario crea la suya con el enlace enviado a su correo.
"""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models import Cargo, Rol, Trabajador, Usuario
from app.schemas.auth import MessageOut
from app.schemas.usuario import UsuarioAdminOut, UsuarioCrearOut, UsuarioIn, UsuarioUpdate
from app.services.acceso_service import enviar_invitacion
from app.services.common import get_or_404
from app.services.usuario_service import (
    activar_usuario,
    actualizar_usuario,
    crear_usuario,
    desactivar_usuario,
)

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


def _admin_out(u: Usuario) -> UsuarioAdminOut:
    return UsuarioAdminOut.model_validate(u)


@router.get("", response_model=list[UsuarioAdminOut])
def listar(
    q: str | None = None,
    activo: bool | None = None,
    rol: str | None = None,
    cargo: str | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    query = db.query(Usuario).join(Trabajador, Usuario.trabajador_id == Trabajador.id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Trabajador.nombres.like(like),
                Trabajador.apellidos.like(like),
                Usuario.email.like(like.lower()),
                Usuario.username.like(like.lower()),
            )
        )
    if activo is not None:
        query = query.filter(Usuario.activo == activo)
    if rol:
        query = query.join(Usuario.roles).filter(Rol.nombre == rol)
    if cargo:
        query = query.join(Cargo, Trabajador.cargo_id == Cargo.id).filter(Cargo.nombre == cargo)
    return query.order_by(Trabajador.apellidos, Trabajador.nombres).all()


@router.get("/{usuario_id}", response_model=UsuarioAdminOut)
def obtener(usuario_id: int, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    return get_or_404(db, Usuario, usuario_id, "Usuario")


@router.post("", response_model=UsuarioCrearOut, status_code=201)
def crear(datos: UsuarioIn, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    """Crea el trabajador y su cuenta. Se envía un correo para que el usuario defina su contraseña."""
    usuario, enviado = crear_usuario(db, datos)
    return UsuarioCrearOut(
        usuario=_admin_out(usuario),
        correo_enviado=enviado,
        mensaje="Usuario creado. Se envió un correo para que defina su contraseña."
        if enviado
        else "Usuario creado, pero no se pudo enviar el correo. Usa «Reenviar invitación».",
    )


@router.patch("/{usuario_id}", response_model=UsuarioAdminOut)
def editar(
    usuario_id: int,
    datos: UsuarioUpdate,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_admin),
):
    return actualizar_usuario(db, get_or_404(db, Usuario, usuario_id, "Usuario"), datos, actor)


@router.post("/{usuario_id}/desactivar", status_code=204)
def desactivar(
    usuario_id: int,
    reemplazo_id: int | None = None,
    sin_relevo: bool = False,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_admin),
):
    """Desactiva al usuario. Si está en la matriz responde 409 EN_MATRIZ hasta indicar `reemplazo_id`."""
    desactivar_usuario(db, get_or_404(db, Usuario, usuario_id, "Usuario"), actor, reemplazo_id, sin_relevo)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{usuario_id}/activar", response_model=UsuarioAdminOut)
def activar(usuario_id: int, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    return activar_usuario(db, get_or_404(db, Usuario, usuario_id, "Usuario"))


@router.post("/{usuario_id}/reenviar-invitacion", response_model=MessageOut)
def reenviar_invitacion(usuario_id: int, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    usuario = get_or_404(db, Usuario, usuario_id, "Usuario")
    if not usuario.activo:
        return MessageOut(mensaje="El usuario está desactivado.")
    enviado = enviar_invitacion(usuario)
    return MessageOut(mensaje="Invitación enviada." if enviado else "No se pudo enviar el correo.")
