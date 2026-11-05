"""Pruebas de Fase 2: catálogos, trabajadores y reemplazos."""
import pytest

from app.core.security import hash_password
from app.models import Trabajador, Usuario


@pytest.fixture()
def admin_headers(client, sample_user):
    r = client.post("/auth/login", json={"username": "apere", "password": "Secret123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def worker_headers(client, db_session, worker_role):
    t = Trabajador(documento="999", nombres="W", apellidos="W")
    db_session.add(t)
    db_session.flush()
    u = Usuario(username="wuser", email="w@example.com", password_hash=hash_password("Worker123!"), trabajador_id=t.id)
    u.roles.append(worker_role)
    db_session.add(u)
    db_session.commit()
    r = client.post("/auth/login", json={"username": "wuser", "password": "Worker123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _area(client, h, nombre="Operaciones"):
    return client.post("/areas", json={"nombre": nombre}, headers=h).json()


def _turno(client, h, nombre="Diurno", ini="07:00:00", fin="15:00:00"):
    return client.post("/tipos-turno", json={"nombre": nombre, "hora_inicio": ini, "hora_fin": fin}, headers=h).json()


def _trab(client, h, doc, **extra):
    return client.post(
        "/trabajadores", json={"documento": doc, "nombres": "N" + doc, "apellidos": "A" + doc, **extra}, headers=h
    )


def test_endpoints_requieren_token(client):
    for ruta in ("/areas", "/cargos", "/tipos-turno", "/trabajadores", "/reemplazos"):
        assert client.get(ruta).status_code == 401


def test_trabajador_no_puede_escribir_pero_si_leer(client, admin_headers, worker_headers):
    assert client.get("/areas", headers=worker_headers).status_code == 403
    assert client.post("/areas", json={"nombre": "X"}, headers=worker_headers).status_code == 403
    assert _trab(client, worker_headers, "1").status_code == 403


def test_catalogos_crud_y_unicidad(client, admin_headers):
    area = _area(client, admin_headers)
    assert client.post("/areas", json={"nombre": "Operaciones"}, headers=admin_headers).status_code == 409
    assert client.post("/cargos", json={"nombre": "Gerente"}, headers=admin_headers).status_code == 422
    cargo = client.post("/cargos", json={"nombre": "Analista", "area_id": area["id"]}, headers=admin_headers)
    assert cargo.status_code == 201
    assert client.post("/cargos", json={"nombre": "Especialista", "area_id": 999}, headers=admin_headers).status_code == 404
    turno = _turno(client, admin_headers)
    assert turno["nombre"] == "Diurno"
    assert client.post(
        "/tipos-turno", json={"nombre": "Z", "hora_inicio": "07:00:00", "hora_fin": "07:00:00"}, headers=admin_headers
    ).status_code == 422
    assert client.patch(f"/areas/{area['id']}", json={"descripcion": "d"}, headers=admin_headers).json()["descripcion"] == "d"
    assert client.delete(f"/areas/{area['id']}", headers=admin_headers).status_code == 204
    assert client.get("/areas?activo=true", headers=admin_headers).json() == []


def test_trabajador_crud_con_usuario(client, admin_headers, worker_role, definir_password):
    area = _area(client, admin_headers)
    cargo = client.post("/cargos", json={"nombre": "Analista", "area_id": area["id"]}, headers=admin_headers).json()
    r = _trab(
        client, admin_headers, "100", area_id=area["id"], cargo_id=cargo["id"],
    )
    assert r.status_code == 201
    assert r.json()["area"]["nombre"] == "Operaciones"
    tid = r.json()["id"]
    acceso = client.post(
        f"/trabajadores/{tid}/usuario",
        json={"email": "n@example.com", "cargo": "Analista"},
        headers=admin_headers,
    )
    assert acceso.status_code == 201
    assert definir_password("n@example.com", "Clave1234!").status_code == 200
    login = client.post("/auth/login", json={"username": "n@example.com", "password": "Clave1234!"})
    assert login.status_code == 200

    assert _trab(client, admin_headers, "100").status_code == 409
    assert client.get("/trabajadores?q=A100", headers=admin_headers).json()[0]["documento"] == "100"
    assert client.patch(f"/trabajadores/{tid}", json={"telefono": "300"}, headers=admin_headers).json()["telefono"] == "300"
    assert client.delete(f"/trabajadores/{tid}", headers=admin_headers).status_code == 204
    assert client.get(f"/trabajadores/{tid}", headers=admin_headers).json()["activo"] is False
    assert client.post("/auth/login", json={"username": "n@example.com", "password": "Clave1234!"}).status_code == 401


def test_trabajador_cargo_de_otra_area(client, admin_headers):
    a1 = _area(client, admin_headers, "A1")
    a2 = _area(client, admin_headers, "A2")
    cargo = client.post("/cargos", json={"nombre": "Analista", "area_id": a1["id"]}, headers=admin_headers).json()
    assert _trab(client, admin_headers, "5", area_id=a2["id"], cargo_id=cargo["id"]).status_code == 422


def test_reemplazos(client, admin_headers):
    t1 = _trab(client, admin_headers, "1").json()["id"]
    t2 = _trab(client, admin_headers, "2").json()["id"]
    t3 = _trab(client, admin_headers, "3").json()["id"]
    turno = _turno(client, admin_headers)["id"]
    base = {"trabajador_ausente_id": t1, "trabajador_reemplazo_id": t2, "tipo_turno_id": turno,
            "fecha_inicio": "2026-01-10", "fecha_fin": "2026-01-12", "motivo": "Incapacidad"}

    ok = client.post("/reemplazos", json=base, headers=admin_headers)
    assert ok.status_code == 201
    assert ok.json()["trabajador_reemplazo"]["id"] == t2

    assert client.post("/reemplazos", json={**base, "trabajador_ausente_id": t3}, headers=admin_headers).status_code == 409
    assert client.post("/reemplazos", json={**base, "trabajador_reemplazo_id": t1}, headers=admin_headers).status_code == 422
    assert client.post("/reemplazos", json={**base, "fecha_fin": "2026-01-01"}, headers=admin_headers).status_code == 422
    assert client.post("/reemplazos", json={**base, "trabajador_reemplazo_id": 999}, headers=admin_headers).status_code == 404

    assert len(client.get(f"/reemplazos?trabajador_id={t1}&desde=2026-01-11", headers=admin_headers).json()) == 1
    assert client.get("/reemplazos?desde=2026-02-01", headers=admin_headers).json() == []

    rid = ok.json()["id"]
    assert client.delete(f"/reemplazos/{rid}", headers=admin_headers).status_code == 204
    assert client.get("/reemplazos", headers=admin_headers).json() == []
    assert client.post("/reemplazos", json=base, headers=admin_headers).status_code == 201


def test_editar_anular_y_reactivar_reemplazo(client, admin_headers):
    a = _trab(client, admin_headers, "REPL-A").json()["id"]
    b = _trab(client, admin_headers, "REPL-B").json()["id"]
    c = _trab(client, admin_headers, "REPL-C").json()["id"]
    body = {
        "trabajador_ausente_id": a,
        "trabajador_reemplazo_id": b,
        "fecha_inicio": "2027-03-01",
        "fecha_fin": "2027-03-03",
        "motivo": "Permiso",
    }
    creado = client.post("/reemplazos", json=body, headers=admin_headers)
    assert creado.status_code == 201
    rid = creado.json()["id"]

    editado = client.patch(
        f"/reemplazos/{rid}",
        json={"trabajador_reemplazo_id": c, "fecha_fin": "2027-03-04", "motivo": "Incapacidad"},
        headers=admin_headers,
    )
    assert editado.status_code == 200
    assert editado.json()["trabajador_reemplazo"]["id"] == c
    assert editado.json()["fecha_fin"] == "2027-03-04"

    assert client.delete(f"/reemplazos/{rid}", headers=admin_headers).status_code == 204
    assert client.get("/reemplazos", headers=admin_headers).json() == []
    historial = client.get("/reemplazos?activo=false", headers=admin_headers).json()
    assert len(historial) == 1 and historial[0]["id"] == rid and historial[0]["activo"] is False
    assert client.post(f"/reemplazos/{rid}/reactivar", headers=admin_headers).status_code == 200
    assert len(client.get("/reemplazos", headers=admin_headers).json()) == 1


def test_reemplazo_no_se_crea_si_reemplazante_tiene_turnos(client, admin_headers, db_session):
    ausente = _trab(client, admin_headers, "CONFLICTO-A").json()["id"]
    reemplazante = _trab(client, admin_headers, "CONFLICTO-B").json()["id"]
    turno = client.post(
        "/tipos-turno",
        json={"nombre": "Turno conflicto", "hora_inicio": "08:00:00", "hora_fin": "16:00:00"},
        headers=admin_headers,
    ).json()
    from app.models import Asignacion
    from datetime import date
    db_session.add(Asignacion(
        trabajador_id=reemplazante,
        fecha=date(2027, 4, 1),
        tipo_turno_id=turno["id"],
        manual=True,
    ))
    db_session.commit()
    r = client.post(
        "/reemplazos",
        json={
            "trabajador_ausente_id": ausente,
            "trabajador_reemplazo_id": reemplazante,
            "tipo_turno_id": turno["id"],
            "fecha_inicio": "2027-04-01",
            "fecha_fin": "2027-04-02",
        },
        headers=admin_headers,
    )
    assert r.status_code == 409


def test_un_ausente_no_puede_tener_dos_coberturas_solapadas(client, admin_headers):
    ausente = _trab(client, admin_headers, "UN-AUSENTE").json()["id"]
    reemplazante_a = _trab(client, admin_headers, "UN-RELEVO-A").json()["id"]
    reemplazante_b = _trab(client, admin_headers, "UN-RELEVO-B").json()["id"]
    base = {
        "trabajador_ausente_id": ausente,
        "fecha_inicio": "2027-05-01",
        "fecha_fin": "2027-05-03",
        "motivo": "Permiso",
    }
    assert client.post(
        "/reemplazos", json={**base, "trabajador_reemplazo_id": reemplazante_a}, headers=admin_headers
    ).status_code == 201
    cruce = client.post(
        "/reemplazos",
        json={**base, "trabajador_reemplazo_id": reemplazante_b},
        headers=admin_headers,
    )
    assert cruce.status_code == 409
