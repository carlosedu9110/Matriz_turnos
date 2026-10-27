"""Endpoints de la matriz de turnos.

Admin: ve y gestiona todo (ciclos, asignaciones, reemplazos).
Usuario final: solo consulta SUS turnos (el filtro se aplica en el servidor, no en la interfaz).
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import es_admin, get_current_active_user, require_admin
from app.db.session import get_db
from app.models import Asignacion, CicloTurno, TipoTurno, Trabajador, Usuario
from app.schemas.matriz import (
    AsignacionManualIn,
    AsignacionOut,
    AsignacionUpdate,
    CicloCreate,
    CicloOut,
    GenerarIn,
    GenerarOut,
    MatrizOut,
)
from app.services.common import commit_or_409, get_or_404
from app.services.matriz_service import construir_matriz, crear_ciclo, generar_asignaciones

router = APIRouter(prefix="/matriz", tags=["matriz"])
admin = Depends(require_admin)


def _ciclo_publico(c: CicloTurno) -> CicloOut:
    """Datos mínimos de la matriz para un Usuario final: sin titulares, relevos ni plantilla."""
    return CicloOut(
        id=c.id, codigo=c.codigo, nombre=c.nombre, fecha_ancla=c.fecha_ancla, activo=c.activo,
        participantes=[], plantilla=[],
    )


@router.post("/ciclos", response_model=CicloOut, status_code=201, dependencies=[admin])
def crear(datos: CicloCreate, db: Session = Depends(get_db)):
    """Crea el ciclo de 4 semanas con sus 4 titulares (fases 1-4) y sus relevos."""
    return crear_ciclo(db, datos)


@router.get("/ciclos", response_model=list[CicloOut])
def listar(db: Session = Depends(get_db), actor: Usuario = Depends(get_current_active_user)):
    ciclos = db.query(CicloTurno).filter(CicloTurno.activo.is_(True)).order_by(CicloTurno.id).all()
    return ciclos if es_admin(actor) else [_ciclo_publico(c) for c in ciclos]


@router.post("/ciclos/{ciclo_id}/generar", response_model=GenerarOut, dependencies=[admin])
def generar(ciclo_id: int, datos: GenerarIn, db: Session = Depends(get_db)):
    """Genera las asignaciones del rango. No toca las manuales ni asigna a personas desactivadas."""
    return generar_asignaciones(db, get_or_404(db, CicloTurno, ciclo_id, "Ciclo"), datos)


@router.get("", response_model=MatrizOut)
def ver_matriz(
    desde: date,
    hasta: date,
    matriz: str | None = None,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(get_current_active_user),
):
    """`matriz` = código (ej. matriz_analistas); si se omite usa la primera activa.

    Un Usuario final recibe únicamente las celdas donde él trabaja o es el titular cubierto.
    """
    if hasta < desde or (hasta - desde).days > 92:
        raise HTTPException(422, "Rango inválido (máximo 93 días)")
    q = db.query(CicloTurno).filter(CicloTurno.activo.is_(True))
    if matriz:
        q = q.filter(CicloTurno.codigo == matriz)
    ciclo = q.order_by(CicloTurno.id).first()
    if matriz and ciclo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Matriz '{matriz}' no encontrada")
    resultado = construir_matriz(db, desde, hasta, ciclo)
    if not es_admin(actor):
        mio = actor.trabajador_id
        resultado.celdas = [
            c for c in resultado.celdas if c.trabajador.id == mio or (c.titular is not None and c.titular.id == mio)
        ]
        resultado.ciclo = _ciclo_publico(ciclo) if ciclo else None
    return resultado


@router.get("/asignaciones", response_model=list[AsignacionOut], dependencies=[admin])
def listar_asignaciones(
    desde: date,
    hasta: date,
    tipo_turno_id: int | None = None,
    trabajador_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Quién está asignado a cada turno (sin aplicar reemplazos): consulta administrativa."""
    if hasta < desde or (hasta - desde).days > 92:
        raise HTTPException(422, "Rango inválido (máximo 93 días)")
    q = db.query(Asignacion).filter(Asignacion.fecha.between(desde, hasta))
    if tipo_turno_id is not None:
        q = q.filter(Asignacion.tipo_turno_id == tipo_turno_id)
    if trabajador_id is not None:
        q = q.filter(Asignacion.trabajador_id == trabajador_id)
    return q.order_by(Asignacion.fecha, Asignacion.tipo_turno_id).all()


@router.put("/asignaciones", status_code=204, dependencies=[admin])
def asignar_manual(datos: AsignacionManualIn, db: Session = Depends(get_db)):
    """Crea o cambia manualmente el turno de una persona en una fecha. No admite personas desactivadas."""
    trabajador = get_or_404(db, Trabajador, datos.trabajador_id, "Trabajador")
    if not trabajador.activo or (trabajador.usuario is not None and not trabajador.usuario.activo):
        raise HTTPException(422, "No se puede asignar a un usuario desactivado")
    if trabajador.usuario is None:
        raise HTTPException(422, "Primero crea una cuenta de usuario para esta persona")
    get_or_404(db, TipoTurno, datos.tipo_turno_id, "Tipo de turno")
    a = (
        db.query(Asignacion)
        .filter(Asignacion.trabajador_id == datos.trabajador_id, Asignacion.fecha == datos.fecha)
        .first()
    )
    if a is None:
        db.add(Asignacion(**datos.model_dump(), manual=True))
    else:
        a.tipo_turno_id, a.manual = datos.tipo_turno_id, True
    commit_or_409(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/asignaciones/{asignacion_id}", response_model=AsignacionOut, dependencies=[admin])
def modificar_asignacion(asignacion_id: int, datos: AsignacionUpdate, db: Session = Depends(get_db)):
    """Modifica persona, fecha o turno de una asignación existente; no admite personal inactivo."""
    asignacion = get_or_404(db, Asignacion, asignacion_id, "Asignación")
    cambios = datos.model_dump(exclude_unset=True)
    if "trabajador_id" in cambios:
        trabajador = get_or_404(db, Trabajador, cambios["trabajador_id"], "Trabajador")
        if not trabajador.activo or (trabajador.usuario is not None and not trabajador.usuario.activo):
            raise HTTPException(422, "No se puede asignar a un usuario desactivado")
        if trabajador.usuario is None:
            raise HTTPException(422, "Primero crea una cuenta de usuario para esta persona")
        asignacion.trabajador_id = trabajador.id
    if "tipo_turno_id" in cambios:
        asignacion.tipo_turno_id = get_or_404(db, TipoTurno, cambios["tipo_turno_id"], "Tipo de turno").id
    if "fecha" in cambios:
        asignacion.fecha = cambios["fecha"]
    asignacion.manual = True
    commit_or_409(db, "La persona ya tiene una asignación en esa fecha")
    db.refresh(asignacion)
    return asignacion


@router.delete("/asignaciones/{asignacion_id}", status_code=204, dependencies=[admin])
def quitar(asignacion_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Asignacion, asignacion_id, "Asignación"))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
