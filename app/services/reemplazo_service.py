"""Reglas de negocio para el ciclo de vida de reemplazos."""
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Asignacion, Reemplazo, TipoTurno, Trabajador, Vacacion
from app.schemas.reemplazo import ReemplazoCreate, ReemplazoUpdate
from app.services.common import commit_or_409, get_or_404


def _validar_participantes(db: Session, ausente_id: int, reemplazante_id: int) -> tuple[Trabajador, Trabajador]:
    ausente = get_or_404(db, Trabajador, ausente_id, "Trabajador ausente")
    reemplazante = get_or_404(db, Trabajador, reemplazante_id, "Trabajador de reemplazo")
    if ausente.id == reemplazante.id:
        raise HTTPException(422, "El trabajador que reemplaza debe ser distinto del ausente")
    if not ausente.activo:
        raise HTTPException(422, "El trabajador ausente está inactivo")
    if ausente.usuario is not None and not ausente.usuario.activo:
        raise HTTPException(422, "El usuario ausente está desactivado")
    if not reemplazante.activo or (reemplazante.usuario is not None and not reemplazante.usuario.activo):
        raise HTTPException(422, "El trabajador de reemplazo debe estar activo")
    return ausente, reemplazante


def _validar_sin_conflictos(
    db: Session,
    ausente_id: int,
    reemplazante_id: int,
    desde: date,
    hasta: date,
    tipo_turno_id: int | None,
    excluir_id: int | None = None,
) -> None:
    if hasta < desde:
        raise HTTPException(422, "La fecha final no puede ser anterior a la fecha inicial")
    if (hasta - desde).days > 366:
        raise HTTPException(422, "El periodo de reemplazo no puede superar 366 días")

    q = db.query(Reemplazo).filter(
        Reemplazo.activo.is_(True),
        Reemplazo.trabajador_reemplazo_id == reemplazante_id,
        Reemplazo.fecha_inicio <= hasta,
        Reemplazo.fecha_fin >= desde,
    )
    if excluir_id is not None:
        q = q.filter(Reemplazo.id != excluir_id)
    cruces = q.all()
    if any(r.tipo_turno_id is None or tipo_turno_id is None or r.tipo_turno_id == tipo_turno_id for r in cruces):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El reemplazante ya tiene otra cobertura que se cruza en esas fechas/turno",
        )

    cobertura_ausente = db.query(Reemplazo).filter(
        Reemplazo.activo.is_(True),
        Reemplazo.trabajador_ausente_id == ausente_id,
        Reemplazo.fecha_inicio <= hasta,
        Reemplazo.fecha_fin >= desde,
    )
    if excluir_id is not None:
        cobertura_ausente = cobertura_ausente.filter(Reemplazo.id != excluir_id)
    if any(
        r.tipo_turno_id is None or tipo_turno_id is None or r.tipo_turno_id == tipo_turno_id
        for r in cobertura_ausente.all()
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El trabajador ausente ya tiene una cobertura que se cruza en esas fechas/turno",
        )

    # La asignación diaria permite un solo turno por persona; no puede a la vez cubrir y mantener el suyo.
    tiene_turnos = db.query(Asignacion.id).filter(
        Asignacion.trabajador_id == reemplazante_id,
        Asignacion.fecha.between(desde, hasta),
    ).first()
    if tiene_turnos:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El reemplazante ya tiene turnos asignados en ese periodo; libera o ajusta primero su programación",
        )


def crear_reemplazo(db: Session, datos: ReemplazoCreate) -> Reemplazo:
    _validar_participantes(db, datos.trabajador_ausente_id, datos.trabajador_reemplazo_id)
    if datos.tipo_turno_id is not None:
        tipo = get_or_404(db, TipoTurno, datos.tipo_turno_id, "Tipo de turno")
        if not tipo.activo:
            raise HTTPException(422, "El tipo de turno está inactivo")
    _validar_sin_conflictos(
        db,
        datos.trabajador_ausente_id,
        datos.trabajador_reemplazo_id,
        datos.fecha_inicio,
        datos.fecha_fin,
        datos.tipo_turno_id,
    )

    reemplazo = Reemplazo(**datos.model_dump())
    db.add(reemplazo)
    commit_or_409(db)
    db.refresh(reemplazo)
    return reemplazo


def actualizar_reemplazo(db: Session, reemplazo_id: int, datos: ReemplazoUpdate) -> Reemplazo:
    reemplazo = get_or_404(db, Reemplazo, reemplazo_id, "Reemplazo")
    if not reemplazo.activo:
        raise HTTPException(409, "No se puede editar un reemplazo anulado")
    if db.query(Vacacion.id).filter(
        Vacacion.reemplazo_id == reemplazo.id,
        Vacacion.estado == "aprobada",
    ).first():
        raise HTTPException(
            409,
            "Este reemplazo pertenece a vacaciones aprobadas; cancela o modifica la solicitud de vacaciones correspondiente",
        )

    cambios = datos.model_dump(exclude_unset=True)
    ausente_id = cambios.get("trabajador_ausente_id", reemplazo.trabajador_ausente_id)
    reemplazante_id = cambios.get("trabajador_reemplazo_id", reemplazo.trabajador_reemplazo_id)
    fecha_inicio = cambios.get("fecha_inicio", reemplazo.fecha_inicio)
    fecha_fin = cambios.get("fecha_fin", reemplazo.fecha_fin)
    tipo_turno_id = cambios.get("tipo_turno_id", reemplazo.tipo_turno_id)
    _validar_participantes(db, ausente_id, reemplazante_id)
    if tipo_turno_id is not None:
        tipo = get_or_404(db, TipoTurno, tipo_turno_id, "Tipo de turno")
        if not tipo.activo:
            raise HTTPException(422, "El tipo de turno está inactivo")
    _validar_sin_conflictos(
        db, ausente_id, reemplazante_id, fecha_inicio, fecha_fin, tipo_turno_id, excluir_id=reemplazo.id
    )
    for campo, valor in cambios.items():
        setattr(reemplazo, campo, valor)
    commit_or_409(db)
    db.refresh(reemplazo)
    return reemplazo


def reactivar_reemplazo(db: Session, reemplazo_id: int) -> Reemplazo:
    reemplazo = get_or_404(db, Reemplazo, reemplazo_id, "Reemplazo")
    if reemplazo.activo:
        raise HTTPException(409, "El reemplazo ya está activo")
    if db.query(Vacacion.id).filter(
        Vacacion.reemplazo_id == reemplazo.id,
        Vacacion.estado == "aprobada",
    ).first():
        raise HTTPException(
            409,
            "Este reemplazo pertenece a vacaciones aprobadas; se gestiona desde la solicitud de vacaciones",
        )
    _validar_participantes(db, reemplazo.trabajador_ausente_id, reemplazo.trabajador_reemplazo_id)
    _validar_sin_conflictos(
        db,
        reemplazo.trabajador_ausente_id,
        reemplazo.trabajador_reemplazo_id,
        reemplazo.fecha_inicio,
        reemplazo.fecha_fin,
        reemplazo.tipo_turno_id,
        excluir_id=reemplazo.id,
    )
    reemplazo.activo = True
    commit_or_409(db)
    db.refresh(reemplazo)
    return reemplazo


def anular_reemplazo(db: Session, reemplazo_id: int) -> None:
    reemplazo = get_or_404(db, Reemplazo, reemplazo_id, "Reemplazo")
    if not reemplazo.activo:
        raise HTTPException(409, "El reemplazo ya está anulado")
    if db.query(Vacacion.id).filter(
        Vacacion.reemplazo_id == reemplazo.id,
        Vacacion.estado == "aprobada",
    ).first():
        raise HTTPException(
            409,
            "Este reemplazo cubre vacaciones aprobadas; cancela o modifica la solicitud de vacaciones correspondiente",
        )
    reemplazo.activo = False
    db.commit()
