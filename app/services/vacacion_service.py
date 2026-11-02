"""Reglas de solicitudes y aprobación de vacaciones."""
from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import es_admin
from app.models import Asignacion, Reemplazo, Trabajador, Usuario, Vacacion
from app.schemas.vacacion import VacacionCreate, VacacionDecision
from app.services.common import commit_or_409, get_or_404

ESTADOS_OCUPANTES = ("pendiente", "aprobada")


def fechas_aprobadas(db: Session, trabajador_id: int, desde: date, hasta: date) -> set[date]:
    """Fechas aprobadas que deben mantenerse libres de nuevas asignaciones laborales."""
    solicitudes = db.query(Vacacion).filter(
        Vacacion.trabajador_id == trabajador_id,
        Vacacion.estado == "aprobada",
        Vacacion.fecha_inicio <= hasta,
        Vacacion.fecha_fin >= desde,
    ).all()
    dias: set[date] = set()
    for solicitud in solicitudes:
        inicio = max(desde, solicitud.fecha_inicio)
        fin = min(hasta, solicitud.fecha_fin)
        while inicio <= fin:
            dias.add(inicio)
            inicio = date.fromordinal(inicio.toordinal() + 1)
    return dias


def _hay_solape(db: Session, trabajador_id: int, desde: date, hasta: date, excluir_id: int | None = None) -> bool:
    q = db.query(Vacacion.id).filter(
        Vacacion.trabajador_id == trabajador_id,
        Vacacion.estado.in_(ESTADOS_OCUPANTES),
        Vacacion.fecha_inicio <= hasta,
        Vacacion.fecha_fin >= desde,
    )
    if excluir_id is not None:
        q = q.filter(Vacacion.id != excluir_id)
    return q.first() is not None


def crear_solicitud(db: Session, trabajador: Trabajador, datos: VacacionCreate) -> Vacacion:
    if not trabajador.activo or (trabajador.usuario is not None and not trabajador.usuario.activo):
        raise HTTPException(422, "Solo un trabajador activo puede solicitar vacaciones")
    if datos.fecha_inicio < date.today():
        raise HTTPException(422, "La fecha de inicio debe ser hoy o una fecha futura")
    if _hay_solape(db, trabajador.id, datos.fecha_inicio, datos.fecha_fin):
        raise HTTPException(409, "Ya existe una solicitud pendiente o aprobada que se cruza con esas fechas")
    solicitud = Vacacion(trabajador_id=trabajador.id, **datos.model_dump(), estado="pendiente")
    db.add(solicitud)
    commit_or_409(db, "La solicitud se cruza con otra solicitud de vacaciones")
    db.refresh(solicitud)
    return solicitud


def listar_solicitudes(
    db: Session,
    actor: Usuario,
    estado: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[Vacacion]:
    q = db.query(Vacacion).options(
        joinedload(Vacacion.trabajador),
        joinedload(Vacacion.reemplazo).joinedload(Reemplazo.trabajador_reemplazo),
    )
    if not es_admin(actor):
        q = q.filter(Vacacion.trabajador_id == actor.trabajador_id)
    if estado is not None:
        q = q.filter(Vacacion.estado == estado)
    if desde is not None:
        q = q.filter(Vacacion.fecha_fin >= desde)
    if hasta is not None:
        q = q.filter(Vacacion.fecha_inicio <= hasta)
    return q.order_by(Vacacion.fecha_inicio, Vacacion.creado_en).all()


def decidir_solicitud(db: Session, vacacion_id: int, datos: VacacionDecision) -> Vacacion:
    solicitud = get_or_404(db, Vacacion, vacacion_id, "Solicitud de vacaciones")
    if solicitud.estado != "pendiente":
        raise HTTPException(409, "Solo se pueden aprobar o rechazar solicitudes pendientes")

    reemplazo = None
    if datos.estado == "aprobada":
        if _hay_solape(
            db, solicitud.trabajador_id, solicitud.fecha_inicio, solicitud.fecha_fin, excluir_id=solicitud.id
        ):
            raise HTTPException(409, "La solicitud se cruza con otra solicitud pendiente o aprobada")
        cobertura_existente = db.query(Reemplazo.id).filter(
            Reemplazo.activo.is_(True),
            Reemplazo.trabajador_ausente_id == solicitud.trabajador_id,
            Reemplazo.fecha_inicio <= solicitud.fecha_fin,
            Reemplazo.fecha_fin >= solicitud.fecha_inicio,
        ).first()
        if cobertura_existente:
            raise HTTPException(409, "Ya existe una cobertura de reemplazo en esas fechas; revisa la programación")
        if datos.reemplazante_id is not None:
            reemplazo_trabajador = get_or_404(db, Trabajador, datos.reemplazante_id, "Reemplazante")
            ausente = get_or_404(db, Trabajador, solicitud.trabajador_id, "Trabajador")
            if reemplazo_trabajador.id == ausente.id:
                raise HTTPException(422, "El reemplazante debe ser otra persona")
            if not reemplazo_trabajador.activo or (
                reemplazo_trabajador.usuario is not None and not reemplazo_trabajador.usuario.activo
            ):
                raise HTTPException(422, "El reemplazante debe estar activo")

            # Evitar aprobar una cobertura si el reemplazante ya trabaja en los mismos días.
            fechas_ausente = {
                row[0]
                for row in db.query(Asignacion.fecha)
                .filter(
                    Asignacion.trabajador_id == ausente.id,
                    Asignacion.fecha.between(solicitud.fecha_inicio, solicitud.fecha_fin),
                )
                .all()
            }
            fechas_reemplazante = {
                row[0]
                for row in db.query(Asignacion.fecha)
                .filter(
                    Asignacion.trabajador_id == reemplazo_trabajador.id,
                    Asignacion.fecha.between(solicitud.fecha_inicio, solicitud.fecha_fin),
                )
                .all()
            }
            if fechas_ausente & fechas_reemplazante:
                raise HTTPException(409, "El reemplazante ya tiene turnos asignados en días que debe cubrir")

            ocupado = db.query(Reemplazo.id).filter(
                Reemplazo.activo.is_(True),
                Reemplazo.trabajador_reemplazo_id == reemplazo_trabajador.id,
                Reemplazo.fecha_inicio <= solicitud.fecha_fin,
                Reemplazo.fecha_fin >= solicitud.fecha_inicio,
            ).first()
            if ocupado:
                raise HTTPException(409, "El reemplazante ya tiene otra cobertura en esas fechas")
            reemplazo = Reemplazo(
                trabajador_ausente_id=ausente.id,
                trabajador_reemplazo_id=reemplazo_trabajador.id,
                fecha_inicio=solicitud.fecha_inicio,
                fecha_fin=solicitud.fecha_fin,
                motivo=f"Vacaciones aprobadas (solicitud #{solicitud.id})",
            )
            db.add(reemplazo)
            db.flush()

    solicitud.estado = datos.estado
    solicitud.nota_admin = datos.nota_admin
    solicitud.reemplazo = reemplazo
    commit_or_409(db, "No se pudo guardar la decisión de vacaciones")
    db.refresh(solicitud)
    return solicitud


def cancelar_solicitud(db: Session, trabajador_id: int, vacacion_id: int) -> None:
    solicitud = get_or_404(db, Vacacion, vacacion_id, "Solicitud de vacaciones")
    if solicitud.trabajador_id != trabajador_id:
        raise HTTPException(404, "Solicitud de vacaciones no encontrada")
    if solicitud.estado != "pendiente":
        raise HTTPException(409, "Solo se pueden cancelar solicitudes pendientes")
    solicitud.estado = "cancelada"
    db.commit()
