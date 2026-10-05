"""Lógica de la matriz de turnos: ciclo rotativo de 4 semanas, generación y vista consolidada."""
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Asignacion,
    CicloParticipante,
    CicloPlantilla,
    CicloTurno,
    Reemplazo,
    TipoTurno,
    Trabajador,
)
from app.schemas.matriz import CeldaOut, CicloCreate, GenerarIn, GenerarOut, MatrizOut, PersonaMini
from app.services.common import commit_or_409, get_or_404

M, T, N = "Mañana", "Tarde", "Noche"

# Turnos base de la operación 24/7 (hora de inicio/fin y color para el frontend).
TURNOS_BASE = [
    (M, "06:00:00", "14:00:00", "#F4B400"),
    (T, "14:00:00", "22:00:00", "#4285F4"),
    (N, "22:00:00", "06:00:00", "#7B1FA2"),
]

# Plantilla del ciclo: semana -> {día (0=lunes..6=domingo): turno}. Los días ausentes son descanso.
PLANTILLA_BASE: dict[int, dict[int, str]] = {
    1: {2: M, 3: M, 4: M, 5: M, 6: M},
    2: {0: T, 1: T, 3: T, 4: T, 5: T},
    3: {0: M, 1: M, 2: T, 4: N, 5: N, 6: N},
    4: {0: N, 1: N, 2: N, 3: N, 6: T},
}


def semana_de_ciclo(ciclo_ancla: date, fase: int, fecha: date) -> int:
    """Semana (1-4) del ciclo que le toca a una fase en una fecha."""
    semanas = (fecha - ciclo_ancla).days // 7
    return (semanas + fase - 1) % 4 + 1


def sembrar_tipos_turno(db: Session) -> dict[str, TipoTurno]:
    from datetime import time

    out = {}
    for nombre, ini, fin, color in TURNOS_BASE:
        tt = db.query(TipoTurno).filter(TipoTurno.nombre == nombre).first()
        if tt is None:
            tt = TipoTurno(
                nombre=nombre,
                hora_inicio=time.fromisoformat(ini),
                hora_fin=time.fromisoformat(fin),
                color=color,
            )
            db.add(tt)
        out[nombre] = tt
    db.commit()
    return out


def crear_ciclo(db: Session, datos: CicloCreate) -> CicloTurno:
    turnos = {t.nombre: t for t in db.query(TipoTurno).filter(TipoTurno.nombre.in_([M, T, N])).all()}
    faltan = {M, T, N} - set(turnos)
    if faltan:
        raise HTTPException(
            422,
            f"Faltan tipos de turno: {', '.join(sorted(faltan))}. Créalos o ejecuta init_db.",
        )
    for p in datos.participantes:
        get_or_404(db, Trabajador, p.trabajador_id, "Titular")
        if p.relevo_id is not None:
            get_or_404(db, Trabajador, p.relevo_id, "Relevo")

    ciclo = CicloTurno(codigo=datos.codigo, nombre=datos.nombre, fecha_ancla=datos.fecha_ancla)
    ciclo.participantes = [CicloParticipante(**p.model_dump()) for p in datos.participantes]
    ciclo.plantilla = [
        CicloPlantilla(semana=sem, dia_semana=dia, tipo_turno_id=turnos[nombre].id)
        for sem, dias in PLANTILLA_BASE.items()
        for dia, nombre in dias.items()
    ]
    db.add(ciclo)
    commit_or_409(db, "Ya existe una matriz con ese código o nombre")
    db.refresh(ciclo)
    return ciclo


def generar_asignaciones(db: Session, ciclo: CicloTurno, datos: GenerarIn) -> GenerarOut:
    plantilla = {(p.semana, p.dia_semana): p.tipo_turno_id for p in ciclo.plantilla}
    existentes = {
        (a.trabajador_id, a.fecha): a
        for a in db.query(Asignacion).filter(Asignacion.fecha.between(datos.desde, datos.hasta))
    }
    creadas = actualizadas = omitidas = 0
    dia = datos.desde
    while dia <= datos.hasta:
        for part in ciclo.participantes:
            turno_id = plantilla.get((semana_de_ciclo(ciclo.fecha_ancla, part.fase, dia), dia.weekday()))
            if turno_id is None:
                continue
            actual = existentes.get((part.trabajador_id, dia))
            if actual is None:
                db.add(
                    Asignacion(trabajador_id=part.trabajador_id, fecha=dia, tipo_turno_id=turno_id, ciclo_id=ciclo.id)
                )
                creadas += 1
            elif datos.sobrescribir and not actual.manual:
                actual.tipo_turno_id, actual.ciclo_id = turno_id, ciclo.id
                actualizadas += 1
            else:
                omitidas += 1
        dia += timedelta(days=1)
    commit_or_409(db)
    return GenerarOut(creadas=creadas, actualizadas=actualizadas, omitidas=omitidas)


def construir_matriz(db: Session, desde: date, hasta: date, ciclo: CicloTurno | None) -> MatrizOut:
    """Asignaciones del rango; si el titular tiene un reemplazo vigente, la celda muestra a quien lo cubre."""
    asignaciones = (
        db.query(Asignacion)
        .options(joinedload(Asignacion.trabajador))
        .filter(Asignacion.fecha.between(desde, hasta))
        .order_by(Asignacion.fecha)
        .all()
    )
    reemplazos = (
        db.query(Reemplazo)
        .options(joinedload(Reemplazo.trabajador_reemplazo))
        .filter(Reemplazo.activo.is_(True), Reemplazo.fecha_inicio <= hasta, Reemplazo.fecha_fin >= desde)
        .all()
    )
    por_ausente: dict[int, list[Reemplazo]] = {}
    for r in reemplazos:
        por_ausente.setdefault(r.trabajador_ausente_id, []).append(r)

    celdas = []
    for a in asignaciones:
        cubierto = next(
            (
                r
                for r in por_ausente.get(a.trabajador_id, [])
                if r.fecha_inicio <= a.fecha <= r.fecha_fin and r.tipo_turno_id in (None, a.tipo_turno_id)
            ),
            None,
        )
        titular = PersonaMini.model_validate(a.trabajador)
        celdas.append(
            CeldaOut(
                asignacion_id=a.id,
                fecha=a.fecha,
                tipo_turno_id=a.tipo_turno_id,
                trabajador=PersonaMini.model_validate(cubierto.trabajador_reemplazo) if cubierto else titular,
                es_reemplazo=cubierto is not None,
                titular=titular if cubierto else None,
                reemplazo_id=cubierto.id if cubierto else None,
                manual=a.manual,
            )
        )
    tipos = db.query(TipoTurno).filter(TipoTurno.activo.is_(True)).order_by(TipoTurno.hora_inicio).all()
    return MatrizOut(desde=desde, hasta=hasta, tipos_turno=tipos, celdas=celdas, ciclo=ciclo)
