"""Endpoints de la matriz de turnos.

Lectura: cualquier usuario autenticado. Escritura: solo Administrador.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_active_user, require_roles
from app.db.session import get_db
from app.models import Asignacion, CicloTurno, TipoTurno, Trabajador
from app.schemas.matriz import AsignacionManualIn, CicloCreate, CicloOut, GenerarIn, GenerarOut, MatrizOut
from app.services.common import commit_or_409, get_or_404
from app.services.matriz_service import construir_matriz, crear_ciclo, generar_asignaciones

router = APIRouter(prefix="/matriz", tags=["matriz"])
admin = Depends(require_roles("Administrador"))
autenticado = Depends(get_current_active_user)


@router.post("/ciclos", response_model=CicloOut, status_code=201, dependencies=[admin])
def crear(datos: CicloCreate, db: Session = Depends(get_db)):
    """Crea el ciclo de 4 semanas con sus 4 titulares (fases 1-4) y sus relevos."""
    return crear_ciclo(db, datos)


@router.get("/ciclos", response_model=list[CicloOut], dependencies=[autenticado])
def listar(db: Session = Depends(get_db)):
    return db.query(CicloTurno).filter(CicloTurno.activo.is_(True)).order_by(CicloTurno.id).all()


@router.post("/ciclos/{ciclo_id}/generar", response_model=GenerarOut, dependencies=[admin])
def generar(ciclo_id: int, datos: GenerarIn, db: Session = Depends(get_db)):
    """Genera las asignaciones del rango. No toca las manuales; sin `sobrescribir` conserva las existentes."""
    return generar_asignaciones(db, get_or_404(db, CicloTurno, ciclo_id, "Ciclo"), datos)


@router.get("", response_model=MatrizOut, dependencies=[autenticado])
def ver_matriz(desde: date, hasta: date, matriz: str | None = None, db: Session = Depends(get_db)):
    """`matriz` = código (ej. matriz_analistas); si se omite usa la primera activa."""
    if hasta < desde or (hasta - desde).days > 92:
        raise HTTPException(422, "Rango inválido (máximo 93 días)")
    q = db.query(CicloTurno).filter(CicloTurno.activo.is_(True))
    if matriz:
        q = q.filter(CicloTurno.codigo == matriz)
    ciclo = q.order_by(CicloTurno.id).first()
    if matriz and ciclo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Matriz '{matriz}' no encontrada")
    return construir_matriz(db, desde, hasta, ciclo)


@router.put("/asignaciones", status_code=204, dependencies=[admin])
def asignar_manual(datos: AsignacionManualIn, db: Session = Depends(get_db)):
    """Crea o cambia manualmente el turno de una persona en una fecha."""
    get_or_404(db, Trabajador, datos.trabajador_id, "Trabajador")
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


@router.delete("/asignaciones/{asignacion_id}", status_code=204, dependencies=[admin])
def quitar(asignacion_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Asignacion, asignacion_id, "Asignación"))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
