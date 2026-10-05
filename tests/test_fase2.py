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
    assert client.get("/areas", headers=worker_headers).status_code == 200
    assert client.post("/areas", json={"nombre": "X"}, headers=worker_headers).status_code == 403
    assert _trab(client, worker_headers, "1").status_code == 403


def test_catalogos_crud_y_unicidad(client, admin_headers):
    area = _area(client, admin_headers)
    assert client.post("/areas", json={"nombre": "Operaciones"}, headers=admin_headers).status_code == 409
    cargo = client.post("/cargos", json={"nombre": "Supervisor", "area_id": area["id"]}, headers=admin_headers)
    assert cargo.status_code == 201
    assert client.post("/cargos", json={"nombre": "X", "area_id": 999}, headers=admin_headers).status_code == 404
    turno = _turno(client, admin_headers)
    assert turno["nombre"] == "Diurno"
    assert client.post(
        "/tipos-turno", json={"nombre": "Z", "hora_inicio": "07:00:00", "hora_fin": "07:00:00"}, headers=admin_headers
    ).status_code == 422
    assert client.patch(f"/areas/{area['id']}", json={"descripcion": "d"}, headers=admin_headers).json()["descripcion"] == "d"
    assert client.delete(f"/areas/{area['id']}", headers=admin_headers).status_code == 204
    assert client.get("/areas?activo=true", headers=admin_headers).json() == []


def test_trabajador_crud_con_usuario(client, admin_headers, worker_role):
    area = _area(client, admin_headers)
    cargo = client.post("/cargos", json={"nombre": "Op", "area_id": area["id"]}, headers=admin_headers).json()
    r = _trab(
        client, admin_headers, "100", area_id=area["id"], cargo_id=cargo["id"],
        usuario={"username": "nuevo", "email": "n@example.com", "password": "Clave1234!"},
    )
    assert r.status_code == 201
    assert r.json()["area"]["nombre"] == "Operaciones"
    login = client.post("/auth/login", json={"username": "nuevo", "password": "Clave1234!"})
    assert login.status_code == 200

    assert _trab(client, admin_headers, "100").status_code == 409
    assert client.get("/trabajadores?q=A100", headers=admin_headers).json()[0]["documento"] == "100"
    tid = r.json()["id"]
    assert client.patch(f"/trabajadores/{tid}", json={"telefono": "300"}, headers=admin_headers).json()["telefono"] == "300"
    assert client.delete(f"/trabajadores/{tid}", headers=admin_headers).status_code == 204
    assert client.get(f"/trabajadores/{tid}", headers=admin_headers).json()["activo"] is False
    assert client.post("/auth/login", json={"username": "nuevo", "password": "Clave1234!"}).status_code == 401


def test_trabajador_cargo_de_otra_area(client, admin_headers):
    a1 = _area(client, admin_headers, "A1")
    a2 = _area(client, admin_headers, "A2")
    cargo = client.post("/cargos", json={"nombre": "C", "area_id": a1["id"]}, headers=admin_headers).json()
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
