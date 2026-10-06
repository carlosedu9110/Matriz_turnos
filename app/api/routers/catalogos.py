"""Endpoints de catálogos: áreas, cargos y tipos de turno.

Lectura: cualquier usuario autenticado. Escritura: solo Administrador.
"""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_active_user, require_roles
from app.db.session import get_db
from app.models import Area, Cargo, TipoTurno
from app.schemas.catalogos import (
    AreaCreate,
    AreaOut,
    AreaUpdate,
    CargoCreate,
    CargoOut,
    CargoUpdate,
    TipoTurnoCreate,
    TipoTurnoOut,
    TipoTurnoUpdate,
)
from app.services.common import commit_or_409, get_or_404

admin = Depends(require_roles("Administrador"))
autenticado = Depends(get_current_active_user)

router = APIRouter(tags=["catálogos"])


def _crear(db: Session, obj):
    db.add(obj)
    commit_or_409(db, "Ya existe un registro con ese nombre")
    db.refresh(obj)
    return obj


def _actualizar(db: Session, obj, datos):
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(obj, campo, valor)
    commit_or_409(db, "Ya existe un registro con ese nombre")
    db.refresh(obj)
    return obj


def _desactivar(db: Session, obj) -> Response:
    obj.activo = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- Áreas ----
@router.get("/areas", response_model=list[AreaOut], dependencies=[autenticado])
def listar_areas(activo: bool | None = None, db: Session = Depends(get_db)):
    q = db.query(Area)
    if activo is not None:
        q = q.filter(Area.activo == activo)
    return q.order_by(Area.nombre).all()


@router.post("/areas", response_model=AreaOut, status_code=201, dependencies=[admin])
def crear_area(datos: AreaCreate, db: Session = Depends(get_db)):
    return _crear(db, Area(**datos.model_dump()))


@router.patch("/areas/{area_id}", response_model=AreaOut, dependencies=[admin])
def actualizar_area(area_id: int, datos: AreaUpdate, db: Session = Depends(get_db)):
    return _actualizar(db, get_or_404(db, Area, area_id, "Área"), datos)


@router.delete("/areas/{area_id}", status_code=204, dependencies=[admin])
def desactivar_area(area_id: int, db: Session = Depends(get_db)):
    return _desactivar(db, get_or_404(db, Area, area_id, "Área"))


# ---- Cargos ----
@router.get("/cargos", response_model=list[CargoOut], dependencies=[autenticado])
def listar_cargos(area_id: int | None = None, activo: bool | None = None, db: Session = Depends(get_db)):
    q = db.query(Cargo)
    if area_id is not None:
        q = q.filter(Cargo.area_id == area_id)
    if activo is not None:
        q = q.filter(Cargo.activo == activo)
    return q.order_by(Cargo.nombre).all()


@router.post("/cargos", response_model=CargoOut, status_code=201, dependencies=[admin])
def crear_cargo(datos: CargoCreate, db: Session = Depends(get_db)):
    if datos.area_id is not None:
        get_or_404(db, Area, datos.area_id, "Área")
    return _crear(db, Cargo(**datos.model_dump()))


@router.patch("/cargos/{cargo_id}", response_model=CargoOut, dependencies=[admin])
def actualizar_cargo(cargo_id: int, datos: CargoUpdate, db: Session = Depends(get_db)):
    if datos.area_id is not None:
        get_or_404(db, Area, datos.area_id, "Área")
    return _actualizar(db, get_or_404(db, Cargo, cargo_id, "Cargo"), datos)


@router.delete("/cargos/{cargo_id}", status_code=204, dependencies=[admin])
def desactivar_cargo(cargo_id: int, db: Session = Depends(get_db)):
    return _desactivar(db, get_or_404(db, Cargo, cargo_id, "Cargo"))


# ---- Tipos de turno ----
@router.get("/tipos-turno", response_model=list[TipoTurnoOut], dependencies=[autenticado])
def listar_tipos_turno(activo: bool | None = None, db: Session = Depends(get_db)):
    q = db.query(TipoTurno)
    if activo is not None:
        q = q.filter(TipoTurno.activo == activo)
    return q.order_by(TipoTurno.hora_inicio).all()


@router.post("/tipos-turno", response_model=TipoTurnoOut, status_code=201, dependencies=[admin])
def crear_tipo_turno(datos: TipoTurnoCreate, db: Session = Depends(get_db)):
    return _crear(db, TipoTurno(**datos.model_dump()))


@router.patch("/tipos-turno/{tipo_id}", response_model=TipoTurnoOut, dependencies=[admin])
def actualizar_tipo_turno(tipo_id: int, datos: TipoTurnoUpdate, db: Session = Depends(get_db)):
    return _actualizar(db, get_or_404(db, TipoTurno, tipo_id, "Tipo de turno"), datos)


@router.delete("/tipos-turno/{tipo_id}", status_code=204, dependencies=[admin])
def desactivar_tipo_turno(tipo_id: int, db: Session = Depends(get_db)):
    return _desactivar(db, get_or_404(db, TipoTurno, tipo_id, "Tipo de turno"))
