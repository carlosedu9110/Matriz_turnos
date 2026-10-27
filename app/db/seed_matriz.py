"""Carga de datos DEMO para ver la matriz funcionando (8 personas ficticias, ciclo y 12 semanas).

Uso:
    python -m app.db.seed_matriz            # demo
Es idempotente: si el ciclo demo ya existe, solo completa asignaciones faltantes.
"""
from datetime import date, timedelta

from app.db.session import SessionLocal
from app.models import CicloTurno, Trabajador
from app.schemas.matriz import CicloCreate, GenerarIn, ParticipanteIn
from app.services.matriz_service import crear_ciclo, generar_asignaciones, sembrar_tipos_turno

NOMBRES = [
    ("Alexandra", "Titular"), ("Jonathan", "Titular"), ("Daniela", "Titular"), ("Yeison", "Titular"),
    ("Cristian", "Relevo"), ("Duban", "Relevo"), ("Paola", "Relevo"), ("Carlos", "Relevo"),
]


def main() -> None:
    db = SessionLocal()
    try:
        sembrar_tipos_turno(db)
        personas = []
        for i, (nombre, rol) in enumerate(NOMBRES, start=1):
            t = db.query(Trabajador).filter(Trabajador.documento == f"DEMO-{i}").first()
            if t is None:
                t = Trabajador(documento=f"DEMO-{i}", nombres=nombre, apellidos=f"({rol} demo)")
                db.add(t)
                db.flush()
            personas.append(t)
        db.commit()

        hoy = date.today()
        lunes = hoy - timedelta(days=hoy.weekday())
        ciclo = db.query(CicloTurno).filter(CicloTurno.codigo == "matriz_analistas").first()
        if ciclo is None:
            ciclo = crear_ciclo(
                db,
                CicloCreate(
                    codigo="matriz_analistas",
                    nombre="Matriz de analistas",
                    fecha_ancla=lunes,
                    participantes=[
                        ParticipanteIn(trabajador_id=personas[i].id, fase=i + 1, relevo_id=personas[i + 4].id)
                        for i in range(4)
                    ],
                ),
            )
        r = generar_asignaciones(db, ciclo, GenerarIn(desde=lunes - timedelta(weeks=4), hasta=lunes + timedelta(weeks=8)))
        print(f"Demo lista. Asignaciones creadas: {r.creadas}, omitidas: {r.omitidas}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
