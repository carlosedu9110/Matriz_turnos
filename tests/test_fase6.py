"""Pruebas de Fase 4: solicitud, cancelación, decisión e integración de vacaciones en la matriz."""
from datetime import date, timedelta

import pytest

from app.core.security import hash_password
from app.models import Asignacion, Reemplazo, Rol, TipoTurno, Trabajador, Usuario, Vacacion
from app.services.matriz_service import sembrar_tipos_turno


def _headers(client, username, password):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def vacation_accounts(db_session, admin_role, worker_role, cargos):
    personas = [
        Trabajador(documento="VAC-1", nombres="Ana", apellidos="Analista", cargo=cargos["Analista"]),
        Trabajador(documento="VAC-2", nombres="Luis", apellidos="Relevo", cargo=cargos["Analista"]),
        Trabajador(documento="VAC-3", nombres="Marta", apellidos="Otra", cargo=cargos["Analista"]),
    ]
    db_session.add_all(personas)
    db_session.flush()
    cuentas = []
    for i, t in enumerate(personas, start=1):
        u = Usuario(
            username=f"vac{i}",
            email=f"vac{i}@example.com",
            password_hash=hash_password("Clave1234!"),
            trabajador_id=t.id,
        )
        u.roles.append(worker_role)
        db_session.add(u)
        cuentas.append(u)
    db_session.commit()
    return {"trabajadores": personas, "usuarios": cuentas}


@pytest.fixture()
def admin_headers(client, sample_user, cargos):
    return _headers(client, "apere", "Secret123!")


@pytest.fixture()
def user_headers(client, vacation_accounts):
    return _headers(client, "vac1", "Clave1234!")


@pytest.fixture()
def fechas():
    desde = date.today() + timedelta(days=10)
    return desde, desde + timedelta(days=4)


def _solicitar(client, headers, desde, hasta, motivo="Descanso"):
    return client.post(
        "/vacaciones",
        json={"fecha_inicio": desde.isoformat(), "fecha_fin": hasta.isoformat(), "motivo": motivo},
        headers=headers,
    )


def test_solicitud_usuario_y_lista_propias(client, user_headers, vacation_accounts, fechas):
    desde, hasta = fechas
    r = _solicitar(client, user_headers, desde, hasta)
    assert r.status_code == 201
    assert r.json()["estado"] == "pendiente"
    assert r.json()["trabajador"]["id"] == vacation_accounts["trabajadores"][0].id
    lista = client.get("/vacaciones", headers=user_headers)
    assert lista.status_code == 200 and len(lista.json()) == 1


def test_usuario_final_solo_ve_sus_solicitudes(client, admin_headers, user_headers, vacation_accounts, fechas):
    desde, hasta = fechas
    otros = _headers(client, "vac2", "Clave1234!")
    assert _solicitar(client, user_headers, desde, hasta).status_code == 201
    assert _solicitar(client, otros, desde, hasta).status_code == 201
    assert [v["trabajador"]["id"] for v in client.get("/vacaciones", headers=user_headers).json()] == [
        vacation_accounts["trabajadores"][0].id
    ]
    assert len(client.get("/vacaciones", headers=admin_headers).json()) == 2


def test_solicitud_valida_fechas_y_sin_solapes(client, user_headers, fechas):
    desde, hasta = fechas
    assert _solicitar(client, user_headers, hasta, desde).status_code == 422
    assert _solicitar(client, user_headers, date.today() - timedelta(days=1), date.today()).status_code == 422
    assert _solicitar(client, user_headers, desde, hasta).status_code == 201
    assert _solicitar(client, user_headers, desde + timedelta(days=1), hasta + timedelta(days=1)).status_code == 409


def test_usuario_cancela_solo_su_solicitud_pendiente(client, user_headers, vacation_accounts, fechas):
    desde, hasta = fechas
    solicitud = _solicitar(client, user_headers, desde, hasta).json()
    otros = _headers(client, "vac2", "Clave1234!")
    assert client.delete(f"/vacaciones/{solicitud['id']}", headers=otros).status_code == 404
    assert client.delete(f"/vacaciones/{solicitud['id']}", headers=user_headers).status_code == 204
    assert client.get("/vacaciones", headers=user_headers).json()[0]["estado"] == "cancelada"
    assert client.delete(f"/vacaciones/{solicitud['id']}", headers=user_headers).status_code == 409


def test_solo_admin_decide_solicitudes(client, user_headers, fechas):
    desde, hasta = fechas
    solicitud = _solicitar(client, user_headers, desde, hasta).json()
    r = client.patch(
        f"/vacaciones/{solicitud['id']}",
        json={"estado": "aprobada"},
        headers=user_headers,
    )
    assert r.status_code == 403


def test_admin_rechaza_con_nota(client, admin_headers, user_headers, fechas):
    desde, hasta = fechas
    solicitud = _solicitar(client, user_headers, desde, hasta).json()
    admin = admin_headers
    r = client.patch(
        f"/vacaciones/{solicitud['id']}",
        json={"estado": "rechazada", "nota_admin": "Periodo no disponible"},
        headers=admin,
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "rechazada" and r.json()["nota_admin"] == "Periodo no disponible"
    assert client.patch(f"/vacaciones/{solicitud['id']}", json={"estado": "aprobada"}, headers=admin).status_code == 409


def test_aprobar_sin_reemplazo_se_refleja_en_matriz(client, admin_headers, user_headers, vacation_accounts, fechas, db_session):
    desde, hasta = fechas
    trabajador = vacation_accounts["trabajadores"][0]
    turno = db_session.query(TipoTurno).filter_by(nombre="Mañana").first()
    if turno is None:
        turno = sembrar_tipos_turno(db_session)["Mañana"]
    db_session.add(Asignacion(trabajador_id=trabajador.id, fecha=desde, tipo_turno_id=turno.id, manual=True))
    db_session.commit()

    solicitud = _solicitar(client, user_headers, desde, hasta).json()
    r = client.patch(
        f"/vacaciones/{solicitud['id']}",
        json={"estado": "aprobada", "nota_admin": "Aprobada"},
        headers=admin_headers,
    )
    assert r.status_code == 200 and r.json()["estado"] == "aprobada"
    matriz = client.get(
        f"/matriz?desde={desde.isoformat()}&hasta={hasta.isoformat()}",
        headers=admin_headers,
    ).json()
    assert len(matriz["vacaciones"]) == 1
    assert matriz["vacaciones"][0]["trabajador"]["id"] == trabajador.id
    assert next(c for c in matriz["celdas"] if c["fecha"] == desde.isoformat())["es_vacaciones"] is True
    # El Usuario final ve su permiso, no vacaciones de compañeros.
    propia = client.get(
        f"/matriz?desde={desde.isoformat()}&hasta={hasta.isoformat()}",
        headers=user_headers,
    ).json()
    assert len(propia["vacaciones"]) == 1


def test_generacion_ciclica_no_asigna_durante_vacaciones_aprobadas(
    client, admin_headers, vacation_accounts, sample_user, db_session
):
    lunes = date.today() - timedelta(days=date.today().weekday())
    miercoles = lunes + timedelta(days=2)
    personas = [*vacation_accounts["trabajadores"], sample_user.trabajador]
    sembrar_tipos_turno(db_session)
    ciclo = client.post(
        "/matriz/ciclos",
        headers=admin_headers,
        json={
            "codigo": "matriz_vacaciones_test",
            "nombre": "Matriz vacaciones test",
            "fecha_ancla": lunes.isoformat(),
            "participantes": [
                {"trabajador_id": persona.id, "fase": fase}
                for fase, persona in enumerate(personas, start=1)
            ],
        },
    )
    assert ciclo.status_code == 201
    trabajador = personas[0]
    db_session.add(Vacacion(
        trabajador_id=trabajador.id,
        fecha_inicio=miercoles,
        fecha_fin=miercoles,
        estado="aprobada",
    ))
    db_session.commit()
    generated = client.post(
        f"/matriz/ciclos/{ciclo.json()['id']}/generar",
        headers=admin_headers,
        json={"desde": miercoles.isoformat(), "hasta": miercoles.isoformat()},
    )
    assert generated.status_code == 200 and generated.json()["omitidas"] == 1
    assert db_session.query(Asignacion).filter_by(trabajador_id=trabajador.id, fecha=miercoles).count() == 0
    turno = db_session.query(TipoTurno).filter_by(nombre="Mañana").one()
    puntual = client.put(
        "/matriz/asignaciones",
        headers=admin_headers,
        json={"trabajador_id": trabajador.id, "fecha": miercoles.isoformat(), "tipo_turno_id": turno.id},
    )
    assert puntual.status_code == 409


def test_aprobar_con_reemplazante_crea_cobertura(client, admin_headers, user_headers, vacation_accounts, fechas):
    desde, hasta = fechas
    ausente, reemplazo = vacation_accounts["trabajadores"][:2]
    solicitud = _solicitar(client, user_headers, desde, hasta).json()
    r = client.patch(
        f"/vacaciones/{solicitud['id']}",
        json={"estado": "aprobada", "reemplazante_id": reemplazo.id},
        headers=admin_headers,
    )
    assert r.status_code == 200 and r.json()["reemplazo_id"] is not None
    matriz = client.get(
        f"/matriz?desde={desde.isoformat()}&hasta={desde.isoformat()}",
        headers=admin_headers,
    ).json()
    assert matriz["vacaciones"][0]["reemplazante"]["id"] == reemplazo.id
    assert client.get("/reemplazos", headers=admin_headers).json()[0]["trabajador_ausente"]["id"] == ausente.id


def test_rechaza_reemplazante_inactivo_o_con_turnos_conflictivos(
    client, admin_headers, user_headers, vacation_accounts, fechas, db_session
):
    desde, hasta = fechas
    ausente, reemplazo, _ = vacation_accounts["trabajadores"]
    turno = sembrar_tipos_turno(db_session)["Mañana"]
    db_session.add(Asignacion(trabajador_id=reemplazo.id, fecha=desde, tipo_turno_id=turno.id, manual=True))
    db_session.add(Asignacion(trabajador_id=ausente.id, fecha=desde, tipo_turno_id=turno.id, manual=True))
    db_session.commit()
    solicitud = _solicitar(client, user_headers, desde, hasta).json()
    r = client.patch(
        f"/vacaciones/{solicitud['id']}",
        json={"estado": "aprobada", "reemplazante_id": reemplazo.id},
        headers=admin_headers,
    )
    assert r.status_code == 409
    assert client.get("/vacaciones", headers=admin_headers).json()[0]["estado"] == "pendiente"


def test_admin_no_duplica_cobertura_existente(client, admin_headers, user_headers, vacation_accounts, fechas, db_session):
    desde, hasta = fechas
    ausente, reemplazo = vacation_accounts["trabajadores"][:2]
    db_session.add(Reemplazo(
        trabajador_ausente_id=ausente.id,
        trabajador_reemplazo_id=reemplazo.id,
        fecha_inicio=desde,
        fecha_fin=hasta,
        motivo="Cobertura previa",
    ))
    db_session.commit()
    solicitud = _solicitar(client, user_headers, desde, hasta).json()
    decision = client.patch(
        f"/vacaciones/{solicitud['id']}",
        json={"estado": "aprobada"},
        headers=admin_headers,
    )
    assert decision.status_code == 409
    assert client.get("/vacaciones", headers=admin_headers).json()[0]["estado"] == "pendiente"


def test_usuario_no_puede_ver_vacaciones_en_matriz_de_otro(
    client, admin_headers, user_headers, fechas, vacation_accounts
):
    desde, hasta = fechas
    otro = _headers(client, "vac2", "Clave1234!")
    solicitud = _solicitar(client, otro, desde, hasta).json()
    client.patch(f"/vacaciones/{solicitud['id']}", json={"estado": "aprobada"}, headers=admin_headers)
    matriz = client.get(
        f"/matriz?desde={desde.isoformat()}&hasta={hasta.isoformat()}",
        headers=user_headers,
    ).json()
    assert matriz["vacaciones"] == []
