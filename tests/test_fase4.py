"""Pruebas de altas/bajas de personal y accesos, con impacto en la matriz."""
from datetime import date, timedelta

import pytest

from app.models import Trabajador
from app.services.matriz_service import sembrar_tipos_turno

HOY = date.today()
LUNES = HOY - timedelta(days=HOY.weekday())


@pytest.fixture()
def admin_headers(client, sample_user):
    r = client.post("/auth/login", json={"username": "apere", "password": "Secret123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def ocho(db_session):
    sembrar_tipos_turno(db_session)
    ts = [Trabajador(documento=f"W{i}", nombres=f"N{i}", apellidos="X") for i in range(9)]
    db_session.add_all(ts)
    db_session.commit()
    return [t.id for t in ts]  # 0-3 titulares, 4-7 relevos, 8 libre


@pytest.fixture()
def matriz(client, admin_headers, ocho):
    body = {
        "codigo": "matriz_analistas",
        "nombre": "Matriz de analistas",
        "fecha_ancla": LUNES.isoformat(),
        "participantes": [{"trabajador_id": ocho[i], "fase": i + 1, "relevo_id": ocho[i + 4]} for i in range(4)],
    }
    cid = client.post("/matriz/ciclos", json=body, headers=admin_headers).json()["id"]
    rango = {"desde": HOY.isoformat(), "hasta": (HOY + timedelta(days=27)).isoformat()}
    client.post(f"/matriz/ciclos/{cid}/generar", json=rango, headers=admin_headers)
    return cid


def _celdas(client, h):
    d = f"desde={HOY}&hasta={HOY + timedelta(days=27)}"
    return client.get(f"/matriz?{d}", headers=h).json()["celdas"]


def test_impacto_titular_y_relevo(client, admin_headers, ocho, matriz):
    t = client.get(f"/trabajadores/{ocho[0]}/impacto", headers=admin_headers).json()
    assert t["en_matriz"] and t["posiciones"][0]["rol"] == "titular" and t["posiciones"][0]["fase"] == 1
    assert t["asignaciones_futuras"] > 0
    r = client.get(f"/trabajadores/{ocho[4]}/impacto", headers=admin_headers).json()
    assert r["posiciones"][0]["rol"] == "relevo" and r["posiciones"][0]["titular"].startswith("N0")
    libre = client.get(f"/trabajadores/{ocho[8]}/impacto", headers=admin_headers).json()
    assert libre["en_matriz"] is False


def test_baja_titular_sin_reemplazo_advierte(client, admin_headers, ocho, matriz):
    r = client.delete(f"/trabajadores/{ocho[0]}", headers=admin_headers)
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["codigo"] == "EN_MATRIZ" and detail["impacto"]["posiciones"][0]["rol"] == "titular"
    assert client.get(f"/trabajadores/{ocho[0]}", headers=admin_headers).json()["activo"] is True


def test_baja_titular_con_reemplazo_traspasa_turnos(client, admin_headers, ocho, matriz):
    antes = [c for c in _celdas(client, admin_headers) if c["trabajador"]["id"] == ocho[0]]
    assert antes
    assert client.delete(f"/trabajadores/{ocho[0]}?reemplazo_id={ocho[8]}", headers=admin_headers).status_code == 204
    despues = _celdas(client, admin_headers)
    assert not [c for c in despues if c["trabajador"]["id"] == ocho[0]]
    assert len([c for c in despues if c["trabajador"]["id"] == ocho[8]]) == len(antes)
    ciclo = client.get("/matriz/ciclos", headers=admin_headers).json()[0]
    fase1 = next(p for p in ciclo["participantes"] if p["fase"] == 1)
    assert fase1["trabajador"]["id"] == ocho[8] and fase1["relevo"]["id"] == ocho[4]
    assert client.get(f"/trabajadores/{ocho[0]}", headers=admin_headers).json()["activo"] is False


def test_baja_relevo_sin_relevo_o_con_reemplazo(client, admin_headers, ocho, matriz):
    assert client.delete(f"/trabajadores/{ocho[4]}", headers=admin_headers).status_code == 409
    assert client.delete(f"/trabajadores/{ocho[4]}?sin_relevo=true", headers=admin_headers).status_code == 204
    ciclo = client.get("/matriz/ciclos", headers=admin_headers).json()[0]
    assert next(p for p in ciclo["participantes"] if p["fase"] == 1)["relevo"] is None
    assert client.delete(f"/trabajadores/{ocho[5]}?reemplazo_id={ocho[8]}", headers=admin_headers).status_code == 204
    ciclo = client.get("/matriz/ciclos", headers=admin_headers).json()[0]
    assert next(p for p in ciclo["participantes"] if p["fase"] == 2)["relevo"]["id"] == ocho[8]


def test_titular_no_admite_sin_relevo(client, admin_headers, ocho, matriz):
    assert client.delete(f"/trabajadores/{ocho[0]}?sin_relevo=true", headers=admin_headers).status_code == 409


def test_reemplazo_invalido(client, admin_headers, ocho, matriz):
    assert client.delete(f"/trabajadores/{ocho[0]}?reemplazo_id={ocho[1]}", headers=admin_headers).status_code == 422
    assert client.delete(f"/trabajadores/{ocho[0]}?reemplazo_id={ocho[0]}", headers=admin_headers).status_code == 422
    assert client.delete(f"/trabajadores/{ocho[0]}?reemplazo_id=9999", headers=admin_headers).status_code == 404


def test_baja_anula_reemplazos_vigentes(client, admin_headers, ocho, matriz):
    d = (HOY + timedelta(days=1)).isoformat()
    client.post(
        "/reemplazos",
        json={"trabajador_ausente_id": ocho[1], "trabajador_reemplazo_id": ocho[8], "fecha_inicio": d, "fecha_fin": d},
        headers=admin_headers,
    )
    assert client.get(f"/trabajadores/{ocho[8]}/impacto", headers=admin_headers).json()["reemplazos_activos"] == 1
    assert client.delete(f"/trabajadores/{ocho[8]}", headers=admin_headers).status_code == 204
    assert client.get("/reemplazos", headers=admin_headers).json() == []


def test_baja_fuera_de_matriz_directa(client, admin_headers, ocho, matriz):
    assert client.delete(f"/trabajadores/{ocho[8]}", headers=admin_headers).status_code == 204
    assert client.delete(f"/trabajadores/{ocho[8]}", headers=admin_headers).status_code == 409


def test_patch_no_permite_baja(client, admin_headers, ocho):
    assert client.patch(f"/trabajadores/{ocho[8]}", json={"activo": False}, headers=admin_headers).status_code == 422


def test_no_puede_darse_de_baja_ni_quitarse_acceso(client, admin_headers, sample_user):
    assert client.delete(f"/trabajadores/{sample_user.trabajador_id}", headers=admin_headers).status_code == 409
    assert client.delete(f"/trabajadores/{sample_user.trabajador_id}/usuario", headers=admin_headers).status_code == 409


def test_dar_y_quitar_acceso(client, admin_headers, ocho, worker_role):
    tid = ocho[8]
    body = {"username": "nuevo", "email": "n@example.com", "password": "Clave1234!", "rol": "Trabajador"}
    r = client.post(f"/trabajadores/{tid}/usuario", json=body, headers=admin_headers)
    assert r.status_code == 201 and r.json()["tiene_usuario"] is True
    assert client.post(f"/trabajadores/{tid}/usuario", json=body, headers=admin_headers).status_code == 409
    assert client.post("/auth/login", json={"username": "nuevo", "password": "Clave1234!"}).status_code == 200

    assert client.delete(f"/trabajadores/{tid}/usuario", headers=admin_headers).status_code == 204
    assert client.get(f"/trabajadores/{tid}", headers=admin_headers).json()["tiene_usuario"] is False
    assert client.post("/auth/login", json={"username": "nuevo", "password": "Clave1234!"}).status_code == 401
    assert client.delete(f"/trabajadores/{tid}/usuario", headers=admin_headers).status_code == 404


def test_ultimo_admin_protegido(client, admin_headers, db_session, ocho, admin_role):
    body = {"username": "otro", "email": "o@example.com", "password": "Clave1234!", "rol": "Administrador"}
    client.post(f"/trabajadores/{ocho[8]}/usuario", json=body, headers=admin_headers)
    otro = {"Authorization": "Bearer " + client.post("/auth/login", json={"username": "otro", "password": "Clave1234!"}).json()["access_token"]}
    # con dos admins, "otro" puede quitar a "apere"; luego "apere" ya no existe y "otro" es el único.
    ap = db_session.query(Trabajador).filter_by(documento="123456789").one()
    assert client.delete(f"/trabajadores/{ap.id}/usuario", headers=otro).status_code == 204
    assert client.delete(f"/trabajadores/{ocho[8]}", headers=otro).status_code == 409


def test_trabajador_no_admin_no_gestiona_personal(client, ocho, db_session, worker_role):
    from app.core.security import hash_password
    from app.models import Usuario

    t = db_session.get(Trabajador, ocho[8])
    u = Usuario(username="w", email="w@example.com", password_hash=hash_password("Worker123!"), trabajador_id=t.id)
    u.roles.append(worker_role)
    db_session.add(u)
    db_session.commit()
    h = {"Authorization": "Bearer " + client.post("/auth/login", json={"username": "w", "password": "Worker123!"}).json()["access_token"]}
    assert client.delete(f"/trabajadores/{ocho[0]}", headers=h).status_code == 403
    assert client.get(f"/trabajadores/{ocho[0]}/impacto", headers=h).status_code == 403
    assert client.post(f"/trabajadores/{ocho[0]}/usuario", json={}, headers=h).status_code in (403, 422)
