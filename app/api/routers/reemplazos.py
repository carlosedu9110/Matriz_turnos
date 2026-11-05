"""Endpoints de reemplazos.

Lectura y escritura: solo rol Admin (el Usuario final ve sus reemplazos reflejados en su matriz).
"""
from datetime import date

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models import Reemplazo
from app.schemas.reemplazo import ReemplazoCreate, ReemplazoOut, ReemplazoUpdate
from app.services.common import get_or_404
from app.services.reemplazo_service import (
    anular_reemplazo,
    actualizar_reemplazo,
    crear_reemplazo,
    reactivar_reemplazo,
)

router = APIRouter(prefix="/reemplazos", tags=["reemplazos"])
admin = Depends(require_admin)


@router.get("", response_model=list[ReemplazoOut], dependencies=[admin])
def listar_reemplazos(
    trabajador_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    activo: bool = True,
    db: Session = Depends(get_db),
):
    """Lista reemplazos; `activo=false` consulta el historial anulado."""
    q = db.query(Reemplazo).filter(Reemplazo.activo.is_(activo))
    if trabajador_id is not None:
        q = q.filter(
            or_(Reemplazo.trabajador_ausente_id == trabajador_id, Reemplazo.trabajador_reemplazo_id == trabajador_id)
        )
    if desde is not None:
        q = q.filter(Reemplazo.fecha_fin >= desde)
    if hasta is not None:
        q = q.filter(Reemplazo.fecha_inicio <= hasta)
    return q.order_by(Reemplazo.fecha_inicio.desc()).all()


@router.get("/{reemplazo_id}", response_model=ReemplazoOut, dependencies=[admin])
def obtener_reemplazo(reemplazo_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Reemplazo, reemplazo_id, "Reemplazo")


@router.post("", response_model=ReemplazoOut, status_code=201, dependencies=[admin])
def crear(datos: ReemplazoCreate, db: Session = Depends(get_db)):
    return crear_reemplazo(db, datos)


@router.patch("/{reemplazo_id}", response_model=ReemplazoOut, dependencies=[admin])
def editar(reemplazo_id: int, datos: ReemplazoUpdate, db: Session = Depends(get_db)):
    """Modifica participantes, turno, periodo o motivo de una cobertura activa."""
    return actualizar_reemplazo(db, reemplazo_id, datos)


@router.post("/{reemplazo_id}/reactivar", response_model=ReemplazoOut, dependencies=[admin])
def reactivar(reemplazo_id: int, db: Session = Depends(get_db)):
    """Reactiva una cobertura anulada solo si sigue sin conflictos."""
    return reactivar_reemplazo(db, reemplazo_id)


@router.delete("/{reemplazo_id}", status_code=204, dependencies=[admin])
def anular(reemplazo_id: int, db: Session = Depends(get_db)):
    """Anula la cobertura conservando el registro histórico."""
    anular_reemplazo(db, reemplazo_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
