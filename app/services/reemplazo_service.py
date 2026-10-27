"""Servicio de reemplazos: validaciones de negocio."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Reemplazo, TipoTurno, Trabajador
from app.schemas.reemplazo import ReemplazoCreate
from app.services.common import commit_or_409, get_or_404


def crear_reemplazo(db: Session, datos: ReemplazoCreate) -> Reemplazo:
    for tid, etiqueta in (
        (datos.trabajador_ausente_id, "Trabajador ausente"),
        (datos.trabajador_reemplazo_id, "Trabajador de reemplazo"),
    ):
        if not get_or_404(db, Trabajador, tid, etiqueta).activo:
            raise HTTPException(422, f"{etiqueta} está inactivo")
    if datos.tipo_turno_id is not None:
        get_or_404(db, TipoTurno, datos.tipo_turno_id, "Tipo de turno")

    # El reemplazante no puede cubrir dos veces el mismo turno en fechas que se cruzan.
    cruce = (
        db.query(Reemplazo)
        .filter(
            Reemplazo.activo.is_(True),
            Reemplazo.trabajador_reemplazo_id == datos.trabajador_reemplazo_id,
            Reemplazo.fecha_inicio <= datos.fecha_fin,
            Reemplazo.fecha_fin >= datos.fecha_inicio,
        )
        .all()
    )
    if any(r.tipo_turno_id is None or datos.tipo_turno_id is None or r.tipo_turno_id == datos.tipo_turno_id for r in cruce):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El trabajador de reemplazo ya tiene un reemplazo que se cruza en esas fechas/turno",
        )

    reemplazo = Reemplazo(**datos.model_dump())
    db.add(reemplazo)
    commit_or_409(db)
    db.refresh(reemplazo)
    return reemplazo
