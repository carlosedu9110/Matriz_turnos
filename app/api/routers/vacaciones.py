"""Solicitudes y aprobación de vacaciones."""
from datetime import date

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_active_user, require_admin
from app.db.session import get_db
from app.models import Usuario
from app.schemas.vacacion import VacacionCreate, VacacionDecision, VacacionOut
from app.services.vacacion_service import (
    cancelar_solicitud,
    crear_solicitud,
    decidir_solicitud,
    listar_solicitudes,
)

router = APIRouter(prefix="/vacaciones", tags=["vacaciones"])


@router.get("", response_model=list[VacacionOut])
def listar(
    estado: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(get_current_active_user),
):
    """Admin ve todas las solicitudes; Usuario final ve solo las propias."""
    return listar_solicitudes(db, actor, estado, desde, hasta)


@router.post("", response_model=VacacionOut, status_code=status.HTTP_201_CREATED)
def solicitar(
    datos: VacacionCreate,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(get_current_active_user),
):
    """Crea una solicitud pendiente para el usuario autenticado."""
    return crear_solicitud(db, actor.trabajador, datos)


@router.delete("/{vacacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancelar(
    vacacion_id: int,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(get_current_active_user),
):
    """El usuario cancela su solicitud mientras siga pendiente."""
    cancelar_solicitud(db, actor.trabajador_id, vacacion_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{vacacion_id}", response_model=VacacionOut, dependencies=[Depends(require_admin)])
def decidir(vacacion_id: int, datos: VacacionDecision, db: Session = Depends(get_db)):
    """Admin aprueba/rechaza; al aprobar puede asignar un reemplazante activo."""
    return decidir_solicitud(db, vacacion_id, datos)
