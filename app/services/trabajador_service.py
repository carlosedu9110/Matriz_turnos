"""Servicio de trabajadores: validaciones de negocio y alta opcional de usuario."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Area, Cargo, Rol, Trabajador, Usuario
from app.schemas.trabajador import TrabajadorCreate
from app.services.common import commit_or_409, get_or_404


def validar_area_cargo(db: Session, area_id: int | None, cargo_id: int | None) -> None:
    area = get_or_404(db, Area, area_id, "Área") if area_id is not None else None
    cargo = get_or_404(db, Cargo, cargo_id, "Cargo") if cargo_id is not None else None
    if area and cargo and cargo.area_id is not None and cargo.area_id != area.id:
        raise HTTPException(
            422, "El cargo no pertenece al área indicada"
        )


def crear_trabajador(db: Session, datos: TrabajadorCreate) -> Trabajador:
    validar_area_cargo(db, datos.area_id, datos.cargo_id)
    trabajador = Trabajador(**datos.model_dump(exclude={"usuario"}))
    db.add(trabajador)

    if datos.usuario is not None:
        rol = db.query(Rol).filter(Rol.nombre == datos.usuario.rol).first()
        if rol is None:
            raise HTTPException(422, f"Rol '{datos.usuario.rol}' no existe")
        trabajador.usuario = Usuario(
            username=datos.usuario.username,
            email=datos.usuario.email,
            password_hash=hash_password(datos.usuario.password),
            roles=[rol],
        )

    commit_or_409(db, "Documento, username o email ya registrados")
    db.refresh(trabajador)
    return trabajador
