"""Endpoints de gestión de trabajadores.

Lectura: cualquier usuario autenticado. Escritura: solo Administrador.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_active_user, require_roles
from app.db.session import get_db
from app.models import Trabajador, Usuario
from app.schemas.trabajador import ImpactoOut, TrabajadorCreate, TrabajadorOut, TrabajadorUpdate, UsuarioCreate
from app.services.common import commit_or_409, get_or_404
from app.services.trabajador_service import (
    calcular_impacto,
    crear_trabajador,
    dar_acceso,
    dar_de_baja,
    quitar_acceso,
    validar_area_cargo,
)

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
    if cambios.get("activo") is False:
        raise HTTPException(422, "Para dar de baja usa DELETE /trabajadores/{id}: valida que no deje vacía la matriz")
    validar_area_cargo(
        db,
        cambios.get("area_id", trabajador.area_id),
        cambios.get("cargo_id", trabajador.cargo_id),
    )
    for campo, valor in cambios.items():
        setattr(trabajador, campo, valor)
    if cambios.get("activo") is True and trabajador.usuario:
        trabajador.usuario.activo = True
    commit_or_409(db, "Ya existe un trabajador con ese documento")
    db.refresh(trabajador)
    return trabajador


@router.get("/{trabajador_id}/impacto", response_model=ImpactoOut, dependencies=[admin])
def impacto(trabajador_id: int, db: Session = Depends(get_db)):
    """Dónde participa el trabajador (matrices, turnos futuros, reemplazos): lo que afecta darlo de baja."""
    return calcular_impacto(db, get_or_404(db, Trabajador, trabajador_id, "Trabajador"))


@router.delete("/{trabajador_id}", status_code=204)
def dar_baja(
    trabajador_id: int,
    reemplazo_id: int | None = None,
    sin_relevo: bool = False,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_roles("Administrador")),
):
    """Baja lógica. Si está en una matriz responde 409 EN_MATRIZ: indica `reemplazo_id` (quien lo sustituye)
    o `sin_relevo=true` (solo si únicamente es relevo)."""
    dar_de_baja(db, get_or_404(db, Trabajador, trabajador_id, "Trabajador"), actor, reemplazo_id, sin_relevo)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{trabajador_id}/usuario", response_model=TrabajadorOut, status_code=201, dependencies=[admin])
def crear_acceso(trabajador_id: int, datos: UsuarioCreate, db: Session = Depends(get_db)):
    """Crea el usuario de acceso de un trabajador que aún no lo tiene."""
    return dar_acceso(db, get_or_404(db, Trabajador, trabajador_id, "Trabajador"), datos)


@router.delete("/{trabajador_id}/usuario", status_code=204)
def eliminar_acceso(
    trabajador_id: int,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_roles("Administrador")),
):
    """Elimina el usuario de acceso (el trabajador y su historial se conservan)."""
    quitar_acceso(db, get_or_404(db, Trabajador, trabajador_id, "Trabajador"), actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)