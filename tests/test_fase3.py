"""Pruebas de Fase 3: ciclo rotativo, generación y vista de la matriz."""
from datetime import date, timedelta

import pytest

from app.models import Trabajador
from app.services.matriz_service import PLANTILLA_BASE, semana_de_ciclo, sembrar_tipos_turno

LUNES = date(2026, 1, 5)


@pytest.fixture()
def admin_headers(client, sample_user):
    r = client.post("/auth/login", json={"username": "apere", "password": "Secret123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def ocho(db_session):
    sembrar_tipos_turno(db_session)
    ts = [Trabajador(documento=f"W{i}", nombres=f"N{i}", apellidos="X") for i in range(8)]
    db_session.add_all(ts)
    db_session.commit()
    return [t.id for t in ts]


def _ciclo(client, h, ids, ancla=LUNES):
    body = {
        "codigo": "matriz_analistas",
        "nombre": "Matriz de analistas",
        "fecha_ancla": ancla.isoformat(),
        "participantes": [{"trabajador_id": ids[i], "fase": i + 1, "relevo_id": ids[i + 4]} for i in range(4)],
    }
    return client.post("/matriz/ciclos", json=body, headers=h)


def test_semana_de_ciclo_rota_cada_semana():
    assert [semana_de_ciclo(LUNES, 1, LUNES + timedelta(weeks=k)) for k in range(5)] == [1, 2, 3, 4, 1]
    assert [semana_de_ciclo(LUNES, f, LUNES) for f in (1, 2, 3, 4)] == [1, 2, 3, 4]


def test_plantilla_cubre_cada_dia_con_mañana_tarde_noche():
    for dia in range(7):
        assert sorted(PLANTILLA_BASE[s][dia] for s in PLANTILLA_BASE if dia in PLANTILLA_BASE[s]) == [
            "Mañana", "Noche", "Tarde"
        ]


def test_crear_ciclo_validaciones(client, admin_headers, ocho):
    assert _ciclo(client, admin_headers, ocho, ancla=LUNES + timedelta(days=1)).status_code == 422
    ok = _ciclo(client, admin_headers, ocho)
    assert ok.status_code == 201
    assert ok.json()["codigo"] == "matriz_analistas"
    assert len(ok.json()["plantilla"]) == 5 + 5 + 6 + 5
    assert _ciclo(client, admin_headers, ocho).status_code == 409


def test_generar_y_ver_matriz(client, admin_headers, ocho):
    cid = _ciclo(client, admin_headers, ocho).json()["id"]
    rango = {"desde": LUNES.isoformat(), "hasta": (LUNES + timedelta(days=27)).isoformat()}
    g = client.post(f"/matriz/ciclos/{cid}/generar", json=rango, headers=admin_headers).json()
    assert g["creadas"] == 4 * 21 and g["omitidas"] == 0
    again = client.post(f"/matriz/ciclos/{cid}/generar", json=rango, headers=admin_headers).json()
    assert again["creadas"] == 0 and again["omitidas"] == 84

    m = client.get(f"/matriz?desde={rango['desde']}&hasta={rango['hasta']}", headers=admin_headers).json()
    por_celda = {}
    for c in m["celdas"]:
        por_celda.setdefault((c["fecha"], c["tipo_turno_id"]), []).append(c)
    assert len(por_celda) == 28 * 3
    assert all(len(v) == 1 for v in por_celda.values())
    assert [t["nombre"] for t in m["tipos_turno"]] == ["Mañana", "Tarde", "Noche"]
    assert m["ciclo"]["codigo"] == "matriz_analistas"
    por_codigo = client.get(f"/matriz?desde={rango['desde']}&hasta={rango['hasta']}&matriz=matriz_analistas", headers=admin_headers)
    assert por_codigo.status_code == 200
    assert client.get("/matriz?desde=2026-01-05&hasta=2026-01-11&matriz=matriz_especialistas", headers=admin_headers).status_code == 404


def test_reemplazo_se_refleja_en_matriz(client, admin_headers, ocho):
    cid = _ciclo(client, admin_headers, ocho).json()["id"]
    d = LUNES + timedelta(days=2)  # miércoles: fase 1 trabaja Mañana
    client.post(f"/matriz/ciclos/{cid}/generar", json={"desde": d.isoformat(), "hasta": d.isoformat()}, headers=admin_headers)
    base = client.get(f"/matriz?desde={d}&hasta={d}", headers=admin_headers).json()["celdas"]
    titular = next(c for c in base if c["trabajador"]["id"] == ocho[0])
    r = client.post(
        "/reemplazos",
        json={"trabajador_ausente_id": ocho[0], "trabajador_reemplazo_id": ocho[4],
              "fecha_inicio": d.isoformat(), "fecha_fin": d.isoformat()},
        headers=admin_headers,
    )
    assert r.status_code == 201
    celdas = client.get(f"/matriz?desde={d}&hasta={d}", headers=admin_headers).json()["celdas"]
    cubierta = next(c for c in celdas if c["asignacion_id"] == titular["asignacion_id"])
    assert cubierta["es_reemplazo"] and cubierta["trabajador"]["id"] == ocho[4]
    assert cubierta["titular"]["id"] == ocho[0]


def test_asignacion_manual_no_se_sobrescribe(client, admin_headers, ocho, db_session):
    cid = _ciclo(client, admin_headers, ocho).json()["id"]
    d = LUNES
    rango = {"desde": d.isoformat(), "hasta": d.isoformat()}
    client.post(f"/matriz/ciclos/{cid}/generar", json=rango, headers=admin_headers)
    tipos = client.get(f"/matriz?desde={d}&hasta={d}", headers=admin_headers).json()["tipos_turno"]
    noche = next(t["id"] for t in tipos if t["nombre"] == "Noche")
    r = client.put("/matriz/asignaciones", json={"trabajador_id": ocho[0], "fecha": d.isoformat(), "tipo_turno_id": noche}, headers=admin_headers)
    assert r.status_code == 204
    client.post(f"/matriz/ciclos/{cid}/generar", json={**rango, "sobrescribir": True}, headers=admin_headers)
    celdas = client.get(f"/matriz?desde={d}&hasta={d}", headers=admin_headers).json()["celdas"]
    mia = next(c for c in celdas if c["trabajador"]["id"] == ocho[0])
    assert mia["tipo_turno_id"] == noche and mia["manual"] is True


def test_permisos_matriz(client, admin_headers, ocho):
    assert client.get("/matriz?desde=2026-01-01&hasta=2026-01-07").status_code == 401
    assert client.get("/matriz?desde=2026-01-07&hasta=2026-01-01", headers=admin_headers).status_code == 422


def test_frontend_servido(client):
    r = client.get("/app/")
    assert r.status_code == 200 and "Matriz de turnos" in r.text
    assert client.get("/app/js/app.js").status_code == 200


def test_plantilla_exacta_segun_matriz_real():
    M, T, N = "Mañana", "Tarde", "Noche"
    assert PLANTILLA_BASE == {
        1: {2: M, 3: M, 4: M, 5: M, 6: M},
        2: {0: T, 1: T, 3: T, 4: T, 5: T},
        3: {0: M, 1: M, 2: T, 4: N, 5: N, 6: N},
        4: {0: N, 1: N, 2: N, 3: N, 6: T},
    }
