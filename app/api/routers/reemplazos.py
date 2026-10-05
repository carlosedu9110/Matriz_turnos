"""Endpoints de reemplazos.

Lectura: cualquier usuario autenticado. Escritura: solo Administrador.
"""
from datetime import date

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_active_user, require_roles
from app.db.session import get_db
from app.models import Reemplazo
from app.schemas.reemplazo import ReemplazoCreate, ReemplazoOut
from app.services.common import get_or_404
from app.services.reemplazo_service import crear_reemplazo

router = APIRouter(prefix="/reemplazos", tags=["reemplazos"])
admin = Depends(require_roles("Administrador"))


@router.get("", response_model=list[ReemplazoOut], dependencies=[Depends(get_current_active_user)])
def listar_reemplazos(
    trabajador_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
):
    """Lista reemplazos activos; `trabajador_id` filtra por ausente o reemplazante; `desde`/`hasta` por solape de fechas."""
    q = db.query(Reemplazo).filter(Reemplazo.activo.is_(True))
    if trabajador_id is not None:
        q = q.filter(
            or_(Reemplazo.trabajador_ausente_id == trabajador_id, Reemplazo.trabajador_reemplazo_id == trabajador_id)
        )
    if desde is not None:
        q = q.filter(Reemplazo.fecha_fin >= desde)
    if hasta is not None:
        q = q.filter(Reemplazo.fecha_inicio <= hasta)
    return q.order_by(Reemplazo.fecha_inicio.desc()).all()


@router.get("/{reemplazo_id}", response_model=ReemplazoOut, dependencies=[Depends(get_current_active_user)])
def obtener_reemplazo(reemplazo_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Reemplazo, reemplazo_id, "Reemplazo")


@router.post("", response_model=ReemplazoOut, status_code=201, dependencies=[admin])
def crear(datos: ReemplazoCreate, db: Session = Depends(get_db)):
    return crear_reemplazo(db, datos)


@router.delete("/{reemplazo_id}", status_code=204, dependencies=[admin])
def anular(reemplazo_id: int, db: Session = Depends(get_db)):
    """Anula el reemplazo (baja lógica)."""
    get_or_404(db, Reemplazo, reemplazo_id, "Reemplazo").activo = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
