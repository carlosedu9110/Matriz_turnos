"""Carga la matriz real `matriz_analistas` (reemplaza los datos DEMO si existen).

Uso:
    python -m app.db.cargar_matriz_real

Idempotente. Los datos personales (documento, apellidos) quedan como PENDIENTE para completarlos luego.
Alineación tomada del Excel (semana del 12-oct-2026): fase 1 Carlos, fase 2 Alexandra, fase 3 Jonathan,
fase 4 Juan Pablo A. Relevos conocidos: Maicol (de Alexandra). Los demás relevos se asignan después.
"""
from datetime import date, timedelta

from app.db.session import SessionLocal
from app.models import Asignacion, CicloTurno, Reemplazo, Trabajador
from app.schemas.matriz import CicloCreate, GenerarIn, ParticipanteIn
from app.services.matriz_service import crear_ciclo, generar_asignaciones, sembrar_tipos_turno

CODIGO = "matriz_analistas"
# Lunes 14-sep-2026 = 4 semanas antes del lunes 12-oct-2026 (misma rotación, ciclo de 4 semanas).
FECHA_ANCLA = date(2026, 9, 14)
GENERAR_DESDE = date(2026, 10, 5)
GENERAR_HASTA = date(2026, 12, 27)

TITULARES = [("Carlos", 1), ("Alexandra", 2), ("Jonathan", 3), ("Juan Pablo A", 4)]
RELEVOS = {"Alexandra": "Maicol"}
# Ausencias ya conocidas del Excel: (ausente, reemplazo, desde, hasta, motivo)
AUSENCIAS = [("Alexandra", "Maicol", date(2026, 10, 12), date(2026, 10, 13), "Vacaciones")]


def _persona(db, nombre: str) -> Trabajador:
    doc = "PENDIENTE-" + nombre.upper().replace(" ", "-")
    t = db.query(Trabajador).filter(Trabajador.documento == doc).first()
    if t is None:
        t = Trabajador(documento=doc, nombres=nombre, apellidos="(completar)")
        db.add(t)
        db.flush()
    return t


def _retirar_demo(db) -> int:
    demo = db.query(Trabajador).filter(Trabajador.documento.like("DEMO-%")).all()
    ids = [t.id for t in demo]
    if not ids:
        return 0
    db.query(Reemplazo).filter(
        Reemplazo.trabajador_ausente_id.in_(ids) | Reemplazo.trabajador_reemplazo_id.in_(ids)
    ).delete(synchronize_session=False)
    db.query(Asignacion).filter(Asignacion.trabajador_id.in_(ids)).delete(synchronize_session=False)
    for c in db.query(CicloTurno).filter(CicloTurno.codigo == CODIGO).all():
        if {p.trabajador_id for p in c.participantes} & set(ids):
            db.delete(c)
    db.flush()
    for t in demo:
        db.delete(t)
    db.commit()
    return len(ids)


def main() -> None:
    db = SessionLocal()
    try:
        sembrar_tipos_turno(db)
        retirados = _retirar_demo(db)
        personas = {n: _persona(db, n) for n, _ in TITULARES}
        personas.update({r: _persona(db, r) for r in RELEVOS.values()})
        db.commit()

        ciclo = db.query(CicloTurno).filter(CicloTurno.codigo == CODIGO).first()
        if ciclo is None:
            ciclo = crear_ciclo(
                db,
                CicloCreate(
                    codigo=CODIGO,
                    nombre="Matriz de analistas",
                    fecha_ancla=FECHA_ANCLA,
                    participantes=[
                        ParticipanteIn(
                            trabajador_id=personas[n].id,
                            fase=fase,
                            relevo_id=personas[RELEVOS[n]].id if n in RELEVOS else None,
                        )
                        for n, fase in TITULARES
                    ],
                ),
            )
        r = generar_asignaciones(db, ciclo, GenerarIn(desde=GENERAR_DESDE, hasta=GENERAR_HASTA))
        for ausente, cubre, desde, hasta, motivo in AUSENCIAS:
            a, c = personas[ausente], personas[cubre]
            ya = db.query(Reemplazo).filter_by(
                trabajador_ausente_id=a.id, trabajador_reemplazo_id=c.id, fecha_inicio=desde, activo=True
            ).first()
            if ya is None:
                db.add(Reemplazo(trabajador_ausente_id=a.id, trabajador_reemplazo_id=c.id,
                                 fecha_inicio=desde, fecha_fin=hasta, motivo=motivo))
        db.commit()
        print(f"Demo retirada: {retirados} personas. Matriz '{CODIGO}' lista. "
              f"Turnos creados: {r.creadas}, ya existentes: {r.omitidas}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
