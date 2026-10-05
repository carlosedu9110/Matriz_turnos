"""Endpoints de gestión de trabajadores.

Lectura: cualquier usuario autenticado. Escritura: solo Administrador.
"""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_active_user, require_roles
from app.db.session import get_db
from app.models import Trabajador
from app.schemas.trabajador import TrabajadorCreate, TrabajadorOut, TrabajadorUpdate
from app.services.common import commit_or_409, get_or_404
from app.services.trabajador_service import crear_trabajador, validar_area_cargo

router = APIRouter(prefix="/trabajadores", tags=["trabajadores"])
admin = Depends(require_roles("Administrador"))


@router.get("", response_model=list[TrabajadorOut], dependencies=[Depends(get_current_active_user)])
def listar_trabajadores(
    q: str | None = None,
    area_id: int | None = None,
    cargo_id: int | None = None,
    activo: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Lista trabajadores; `q` busca por documento, nombres o apellidos."""
    query = db.query(Trabajador)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(Trabajador.documento.like(like), Trabajador.nombres.like(like), Trabajador.apellidos.like(like))
        )
    if area_id is not None:
        query = query.filter(Trabajador.area_id == area_id)
    if cargo_id is not None:
        query = query.filter(Trabajador.cargo_id == cargo_id)
    if activo is not None:
        query = query.filter(Trabajador.activo == activo)
    return query.order_by(Trabajador.apellidos, Trabajador.nombres).offset(skip).limit(min(limit, 500)).all()


@router.get("/{trabajador_id}", response_model=TrabajadorOut, dependencies=[Depends(get_current_active_user)])
def obtener_trabajador(trabajador_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Trabajador, trabajador_id, "Trabajador")


@router.post("", response_model=TrabajadorOut, status_code=201, dependencies=[admin])
def crear(datos: TrabajadorCreate, db: Session = Depends(get_db)):
    return crear_trabajador(db, datos)


@router.patch("/{trabajador_id}", response_model=TrabajadorOut, dependencies=[admin])
def actualizar(trabajador_id: int, datos: TrabajadorUpdate, db: Session = Depends(get_db)):
    trabajador = get_or_404(db, Trabajador, trabajador_id, "Trabajador")
    cambios = datos.model_dump(exclude_unset=True)
    validar_area_cargo(
        db,
        cambios.get("area_id", trabajador.area_id),
        cambios.get("cargo_id", trabajador.cargo_id),
    )
    for campo, valor in cambios.items():
        setattr(trabajador, campo, valor)
    commit_or_409(db, "Ya existe un trabajador con ese documento")
    db.refresh(trabajador)
    return trabajador


@router.delete("/{trabajador_id}", status_code=204, dependencies=[admin])
def desactivar(trabajador_id: int, db: Session = Depends(get_db)):
    """Baja lógica: el trabajador queda inactivo (conserva su historial)."""
    trabajador = get_or_404(db, Trabajador, trabajador_id, "Trabajador")
    trabajador.activo = False
    if trabajador.usuario:
        trabajador.usuario.activo = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
