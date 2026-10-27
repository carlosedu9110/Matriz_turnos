"""Pruebas de roles (Admin / Usuario final), cargos, alta de usuarios, correo y permisos."""
from datetime import date, timedelta

import pytest

from app.core.security import create_reset_token
from app.models import Cargo, Rol, Trabajador, Usuario
from app.services.matriz_service import sembrar_tipos_turno

HOY = date.today()
LUNES = HOY - timedelta(days=HOY.weekday())


def _headers(client, ident, password):
    r = client.post("/auth/login", json={"username": ident, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _nuevo(client, h, email="maria@example.com", **kw):
    body = {"nombres": "María", "apellidos": "López", "email": email, "telefono": "3001234567", "cargo": "Analista", **kw}
    return client.post("/usuarios", json=body, headers=h)


@pytest.fixture()
def admin_headers(client, sample_user, worker_role, cargos):
    return _headers(client, "apere", "Secret123!")


@pytest.fixture()
def final(client, admin_headers, definir_password):
    """Usuario final (cargo Analista) creado por el Admin que define su propia contraseña."""
    r = _nuevo(client, admin_headers, "final@example.com")
    assert r.status_code == 201
    assert definir_password("final@example.com", "Final1234!").status_code == 200
    u = r.json()["usuario"]
    return {"h": _headers(client, "final@example.com", "Final1234!"), "uid": u["id"], "tid": u["trabajador_id"]}


# ---------- Creación de usuarios ----------
def test_admin_crea_usuario_con_todos_los_datos(client, admin_headers, correo_en_memoria, definir_password):
    r = _nuevo(client, admin_headers, "Maria@Example.com")
    assert r.status_code == 201
    body = r.json()
    u = body["usuario"]
    assert (u["nombres"], u["apellidos"], u["telefono"], u["cargo"]) == ("María", "López", "3001234567", "Analista")
    assert u["email"] == "maria@example.com"  # el correo se normaliza
    assert [x["nombre"] for x in u["roles"]] == ["Usuario final"] and body["correo_enviado"] is True
    assert "password" not in str(body).lower() and "hash" not in str(body).lower()

    # El correo lleva el enlace para definir la contraseña; hasta entonces nadie puede entrar.
    assert correo_en_memoria[-1]["to"] == "maria@example.com" and "#reset=" in correo_en_memoria[-1]["body"]
    assert client.post("/auth/login", json={"username": "maria@example.com", "password": "Cualquiera1!"}).status_code == 401
    assert definir_password("maria@example.com", "MiClave1234!").status_code == 200
    h = _headers(client, "maria@example.com", "MiClave1234!")
    me = client.get("/auth/me", headers=h).json()
    assert me["cargo"] == "Analista" and me["telefono"] == "3001234567" and me["roles"][0]["nombre"] == "Usuario final"


@pytest.mark.parametrize(
    "cambio",
    [
        {"email": None},
        {"email": "no-es-un-correo"},
        {"email": "sin@dominio"},
        {"telefono": None},
        {"nombres": "  "},
        {"apellidos": None},
        {"cargo": "Gerente"},
        {"cargo": None},
        {"rol": "Administrador"},
    ],
)
def test_validaciones_de_creacion(client, admin_headers, cambio):
    body = {"nombres": "A", "apellidos": "B", "email": "a@example.com", "telefono": "3000000", "cargo": "Analista", **cambio}
    body = {k: v for k, v in body.items() if v is not None}
    assert client.post("/usuarios", json=body, headers=admin_headers).status_code == 422


def test_correo_unico_sin_importar_mayusculas(client, admin_headers):
    assert _nuevo(client, admin_headers, "dup@example.com").status_code == 201
    assert _nuevo(client, admin_headers, "DUP@example.com").status_code == 409
    assert client.get("/usuarios?q=dup", headers=admin_headers).json()[0]["email"] == "dup@example.com"


def test_vincular_trabajador_exige_cargo_permitido(client, admin_headers):
    worker = client.post(
        "/trabajadores",
        json={"documento": "SIN-CUENTA", "nombres": "Persona", "apellidos": "Existente"},
        headers=admin_headers,
    ).json()
    url = f"/trabajadores/{worker['id']}/usuario"
    assert client.post(url, json={"email": "persona@example.com"}, headers=admin_headers).status_code == 422
    assert client.post(
        url,
        json={"email": "persona@example.com", "cargo": "Gerente"},
        headers=admin_headers,
    ).status_code == 422
    assert client.post(
        url,
        json={"email": "persona@example.com", "cargo": "Analista", "rol": "Usuario final"},
        headers=admin_headers,
    ).status_code == 201


def test_alta_heredada_de_trabajador_con_usuario_exige_cargo(client, admin_headers):
    base = {"documento": "NUEVO-TRAB", "nombres": "Ana", "apellidos": "López"}
    assert client.post(
        "/trabajadores",
        json={**base, "usuario": {"email": "sin-cargo@example.com"}},
        headers=admin_headers,
    ).status_code == 422
    r = client.post(
        "/trabajadores",
        json={**base, "usuario": {"email": "con-cargo@example.com", "cargo": "Analista", "rol": "Usuario final"}},
        headers=admin_headers,
    )
    assert r.status_code == 201 and r.json()["cargo"]["nombre"] == "Analista"


def test_cargos_y_roles_disponibles(client, admin_headers, db_session):
    for cargo in ("Analista", "Especialista", "Admin"):
        assert _nuevo(client, admin_headers, f"{cargo.lower()}@example.com", cargo=cargo).status_code == 201
    assert client.post("/cargos", json={"nombre": "Analista"}, headers=admin_headers).status_code == 409
    assert {c.nombre for c in db_session.query(Cargo)} == {"Analista", "Especialista", "Admin"}
    assert {r.nombre for r in db_session.query(Rol)} == {"Admin", "Usuario final"}


# ---------- Rol y cargo son independientes ----------
def test_permisos_dependen_del_rol_no_del_cargo(client, admin_headers, definir_password):
    # Cargo Admin pero rol Usuario final: sin permisos administrativos.
    _nuevo(client, admin_headers, "cargo-admin@example.com", cargo="Admin", rol="Usuario final")
    definir_password("cargo-admin@example.com", "Clave1234!")
    h1 = _headers(client, "cargo-admin@example.com", "Clave1234!")
    assert client.get("/auth/me", headers=h1).json()["cargo"] == "Admin"
    assert client.get("/usuarios", headers=h1).status_code == 403
    # Cargo Especialista pero rol Admin: acceso administrativo total.
    _nuevo(client, admin_headers, "rol-admin@example.com", cargo="Especialista", rol="Admin")
    definir_password("rol-admin@example.com", "Clave1234!")
    h2 = _headers(client, "rol-admin@example.com", "Clave1234!")
    assert client.get("/usuarios", headers=h2).status_code == 200
    assert _nuevo(client, h2, "otro@example.com").status_code == 201


# ---------- Seguridad: el servidor valida, no la interfaz ----------
ENDPOINTS_ADMIN = [
    ("get", "/usuarios"), ("get", "/usuarios/1"), ("post", "/usuarios"), ("patch", "/usuarios/1"),
    ("post", "/usuarios/1/desactivar"), ("post", "/usuarios/1/activar"), ("post", "/usuarios/1/reenviar-invitacion"),
    ("get", "/trabajadores"), ("post", "/trabajadores"), ("patch", "/trabajadores/1"), ("delete", "/trabajadores/1"),
    ("get", "/trabajadores/1/impacto"), ("post", "/trabajadores/1/usuario"), ("delete", "/trabajadores/1/usuario"),
    ("get", "/reemplazos"), ("get", "/reemplazos/1"), ("post", "/reemplazos"), ("delete", "/reemplazos/1"),
    ("post", "/matriz/ciclos"), ("post", "/matriz/ciclos/1/generar"),
    ("get", "/matriz/asignaciones?desde=2026-01-01&hasta=2026-01-07"),
    ("patch", "/matriz/asignaciones/1"),
    ("put", "/matriz/asignaciones"), ("delete", "/matriz/asignaciones/1"),
    ("post", "/areas"), ("patch", "/areas/1"), ("delete", "/areas/1"),
    ("get", "/areas"),
    ("post", "/cargos"), ("patch", "/cargos/1"), ("delete", "/cargos/1"),
    ("get", "/cargos"),
    ("post", "/tipos-turno"), ("patch", "/tipos-turno/1"), ("delete", "/tipos-turno/1"),
    ("get", "/tipos-turno"),
]


@pytest.mark.parametrize("metodo,ruta", ENDPOINTS_ADMIN)
def test_usuario_final_no_accede_a_funciones_admin(client, final, metodo, ruta):
    sin_token = client.request(metodo, ruta, json={})
    assert sin_token.status_code == 401
    con_rol_final = client.request(metodo, ruta, json={}, headers=final["h"])
    assert con_rol_final.status_code == 403, f"{metodo.upper()} {ruta} -> {con_rol_final.status_code}"


def test_usuario_final_solo_consulta_su_informacion(client, admin_headers, final):
    otro = _nuevo(client, admin_headers, "otro@example.com").json()["usuario"]
    assert client.get(f"/trabajadores/{final['tid']}", headers=final["h"]).status_code == 200
    assert client.get(f"/trabajadores/{otro['trabajador_id']}", headers=final["h"]).status_code == 403
    assert client.get("/auth/me", headers=final["h"]).json()["email"] == "final@example.com"


def test_admin_nunca_recibe_contrasenas(client, admin_headers, db_session):
    _nuevo(client, admin_headers, "x@example.com")
    for ruta in ("/usuarios", "/usuarios/1", "/auth/me", "/trabajadores"):
        texto = client.get(ruta, headers=admin_headers).text.lower()
        assert "password" not in texto and "hash" not in texto and "$2b$" not in texto
    # La cuenta nueva nace con una clave aleatoria desconocida (no hay forma de adivinarla).
    nuevo = db_session.query(Usuario).filter_by(email="x@example.com").one()
    assert nuevo.password_hash.startswith("$2b$")
    assert client.post("/auth/login", json={"username": "x@example.com", "password": "Admin123!"}).status_code == 401


# ---------- Recuperación de contraseña por correo ----------
def test_recuperacion_de_contrasena(client, final, correo_en_memoria, definir_password):
    correo_en_memoria.clear()
    existe = client.post("/auth/forgot-password", json={"email": "FINAL@example.com"})
    no_existe = client.post("/auth/forgot-password", json={"email": "nadie@example.com"})
    assert existe.status_code == no_existe.status_code == 200 and existe.json() == no_existe.json()
    assert [m["to"] for m in correo_en_memoria] == ["final@example.com"]  # solo a la cuenta real

    assert definir_password("final@example.com", "NuevaClave123!").status_code == 200
    assert client.post("/auth/login", json={"username": "final@example.com", "password": "Final1234!"}).status_code == 401
    assert client.post("/auth/login", json={"username": "final@example.com", "password": "NuevaClave123!"}).status_code == 200
    # El enlace es de un solo uso.
    assert definir_password("final@example.com", "OtraClave1234!").status_code == 400


def test_recuperacion_rechaza_tokens_invalidos(client, final, db_session):
    u = db_session.query(Usuario).filter_by(email="final@example.com").one()
    vencido = create_reset_token(u.email, u.password_hash, timedelta(seconds=-5))
    assert client.post("/auth/reset-password", json={"token": vencido, "new_password": "NuevaClave123!"}).status_code == 400
    acceso = final["h"]["Authorization"].split()[1]  # un token de sesión no sirve como enlace de recuperación
    assert client.post("/auth/reset-password", json={"token": acceso, "new_password": "NuevaClave123!"}).status_code == 400
    ok = create_reset_token(u.email, u.password_hash, timedelta(minutes=5))
    assert client.post("/auth/reset-password", json={"token": ok, "new_password": "corta"}).status_code == 422
    assert client.post("/auth/reset-password", json={"token": "basura-basura", "new_password": "NuevaClave123!"}).status_code == 400


def test_cuentas_desactivadas_no_recuperan_acceso(client, admin_headers, final, correo_en_memoria):
    assert client.post(f"/usuarios/{final['uid']}/desactivar", headers=admin_headers).status_code == 204
    correo_en_memoria.clear()
    client.post("/auth/forgot-password", json={"email": "final@example.com"})
    assert correo_en_memoria == []


def test_login_con_correo_y_formulario_swagger(client, final):
    assert client.post("/auth/token", data={"username": "final@example.com", "password": "Final1234!"}).status_code == 200
    assert client.post("/auth/login", json={"username": "final@example.com", "password": "mala"}).status_code == 401


# ---------- Editar y desactivar ----------
def test_admin_edita_usuarios(client, admin_headers, final, sample_user):
    otro = _nuevo(client, admin_headers, "otro@example.com").json()["usuario"]
    r = client.patch(
        f"/usuarios/{final['uid']}",
        json={"nombres": "Luisa", "telefono": "3109999999", "cargo": "Especialista", "email": "NUEVO@example.com"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    u = r.json()
    assert (u["nombres"], u["telefono"], u["cargo"], u["email"]) == ("Luisa", "3109999999", "Especialista", "nuevo@example.com")
    assert client.patch(f"/usuarios/{final['uid']}", json={"email": "otro@example.com"}, headers=admin_headers).status_code == 409
    assert client.patch(f"/usuarios/{final['uid']}", json={"cargo": "Gerente"}, headers=admin_headers).status_code == 422
    no_aplicado = client.patch(
        f"/usuarios/{final['uid']}", json={"nombres": "No aplicar", "cargo": "Gerente"}, headers=admin_headers
    )
    assert no_aplicado.status_code == 422
    assert client.get(f"/usuarios/{final['uid']}", headers=admin_headers).json()["nombres"] == "Luisa"
    # Cambiar el rol: permitido sobre otros, nunca sobre uno mismo.
    ascenso = client.patch(f"/usuarios/{otro['id']}", json={"rol": "Admin"}, headers=admin_headers)
    assert [x["nombre"] for x in ascenso.json()["roles"]] == ["Admin"]
    assert client.patch(
        f"/usuarios/{sample_user.id}",
        json={"rol": "Usuario final", "nombres": "No cambiar"},
        headers=admin_headers,
    ).status_code == 409
    assert client.get(f"/usuarios/{sample_user.id}", headers=admin_headers).json()["nombres"] == "Ana"


def test_desactivar_y_activar_usuario(client, admin_headers, final):
    assert client.post(f"/usuarios/{final['uid']}/desactivar", headers=admin_headers).status_code == 204
    assert client.get("/auth/me", headers=final["h"]).status_code == 401  # su sesión deja de valer
    assert client.post("/auth/login", json={"username": "final@example.com", "password": "Final1234!"}).status_code == 401
    assert client.get("/usuarios?activo=false", headers=admin_headers).json()[0]["email"] == "final@example.com"
    assert client.post(f"/usuarios/{final['uid']}/activar", headers=admin_headers).json()["activo"] is True
    assert client.post("/auth/login", json={"username": "final@example.com", "password": "Final1234!"}).status_code == 200


def test_admin_no_puede_desactivarse(client, admin_headers, sample_user):
    assert client.post(f"/usuarios/{sample_user.id}/desactivar", headers=admin_headers).status_code == 409


def test_reenviar_invitacion(client, admin_headers, correo_en_memoria):
    uid = _nuevo(client, admin_headers, "inv@example.com").json()["usuario"]["id"]
    correo_en_memoria.clear()
    assert client.post(f"/usuarios/{uid}/reenviar-invitacion", headers=admin_headers).status_code == 200
    assert [m["to"] for m in correo_en_memoria] == ["inv@example.com"]


# ---------- Asignación de turnos ----------
@pytest.fixture()
def matriz(client, admin_headers, db_session):
    sembrar_tipos_turno(db_session)
    ts = [Trabajador(documento=f"W{i}", nombres=f"N{i}", apellidos="X") for i in range(6)]
    db_session.add_all(ts)
    db_session.commit()
    ids = [t.id for t in ts]
    body = {
        "codigo": "matriz_analistas", "nombre": "Matriz de analistas", "fecha_ancla": LUNES.isoformat(),
        "participantes": [{"trabajador_id": ids[i], "fase": i + 1} for i in range(4)],
    }
    cid = client.post("/matriz/ciclos", json=body, headers=admin_headers).json()["id"]
    rango = {"desde": LUNES.isoformat(), "hasta": (LUNES + timedelta(days=27)).isoformat()}
    client.post(f"/matriz/ciclos/{cid}/generar", json=rango, headers=admin_headers)
    return {"ids": ids, "cid": cid, "rango": rango}


def test_usuario_final_solo_ve_sus_turnos(client, admin_headers, matriz, definir_password, worker_role):
    mio = matriz["ids"][0]
    assert client.post(
        f"/trabajadores/{mio}/usuario",
        json={"email": "yo@example.com", "cargo": "Analista"},
        headers=admin_headers,
    ).status_code == 201
    definir_password("yo@example.com", "Clave1234!")
    h = _headers(client, "yo@example.com", "Clave1234!")
    r = matriz["rango"]
    propio = client.get(f"/matriz?desde={r['desde']}&hasta={r['hasta']}", headers=h).json()
    todo = client.get(f"/matriz?desde={r['desde']}&hasta={r['hasta']}", headers=admin_headers).json()
    assert 0 < len(propio["celdas"]) < len(todo["celdas"])
    assert all(c["trabajador"]["id"] == mio for c in propio["celdas"])
    assert propio["ciclo"]["participantes"] == [] and propio["ciclo"]["plantilla"] == []
    assert all(c["participantes"] == [] for c in client.get("/matriz/ciclos", headers=h).json())
    assert len(todo["ciclo"]["participantes"]) == 4


def test_admin_asigna_modifica_y_elimina(client, admin_headers, matriz):
    libre, d = matriz["ids"][4], (LUNES + timedelta(days=1)).isoformat()
    assert client.post(
        f"/trabajadores/{libre}/usuario",
        json={"email": "asignable@example.com", "cargo": "Analista"},
        headers=admin_headers,
    ).status_code == 201
    tipos = {t["nombre"]: t["id"] for t in client.get(f"/matriz?desde={d}&hasta={d}", headers=admin_headers).json()["tipos_turno"]}
    put = lambda tipo: client.put(  # noqa: E731
        "/matriz/asignaciones", json={"trabajador_id": libre, "fecha": d, "tipo_turno_id": tipo}, headers=admin_headers
    )
    assert put(tipos["Tarde"]).status_code == 204
    fila = client.get(f"/matriz/asignaciones?desde={d}&hasta={d}&trabajador_id={libre}", headers=admin_headers).json()
    assert len(fila) == 1 and fila[0]["tipo_turno_id"] == tipos["Tarde"] and fila[0]["trabajador"]["id"] == libre
    assert client.patch(
        f"/matriz/asignaciones/{fila[0]['id']}",
        json={"tipo_turno_id": tipos["Noche"]},
        headers=admin_headers,
    ).status_code == 200
    fila = client.get(f"/matriz/asignaciones?desde={d}&hasta={d}&tipo_turno_id={tipos['Noche']}", headers=admin_headers).json()
    assert [f["trabajador"]["id"] for f in fila if f["trabajador"]["id"] == libre] == [libre]
    asignacion_id = next(f["id"] for f in fila if f["trabajador"]["id"] == libre)
    assert client.delete(f"/matriz/asignaciones/{asignacion_id}", headers=admin_headers).status_code == 204
    assert client.get(f"/matriz/asignaciones?desde={d}&hasta={d}&trabajador_id={libre}", headers=admin_headers).json() == []


def test_no_se_asigna_a_usuarios_desactivados(client, admin_headers, matriz, definir_password, db_session):
    libre, d = matriz["ids"][4], (LUNES + timedelta(days=2)).isoformat()
    tipo = client.get(f"/matriz?desde={d}&hasta={d}", headers=admin_headers).json()["tipos_turno"][0]["id"]
    body = {"trabajador_id": libre, "fecha": d, "tipo_turno_id": tipo}
    client.post(
        f"/trabajadores/{libre}/usuario",
        json={"email": "baja@example.com", "cargo": "Analista"},
        headers=admin_headers,
    )
    uid = db_session.query(Usuario).filter_by(email="baja@example.com").one().id
    assert client.put("/matriz/asignaciones", json=body, headers=admin_headers).status_code == 204
    assert client.post(f"/usuarios/{uid}/desactivar", headers=admin_headers).status_code == 204
    r = client.put("/matriz/asignaciones", json=body, headers=admin_headers)
    assert r.status_code == 422 and "desactivado" in r.json()["detail"]
    # La generación automática tampoco asigna a participantes desactivados.
    part = db_session.get(Trabajador, matriz["ids"][1])
    part.activo = False
    db_session.commit()
    nueva = {"desde": (LUNES + timedelta(days=28)).isoformat(), "hasta": (LUNES + timedelta(days=34)).isoformat()}
    client.post(f"/matriz/ciclos/{matriz['cid']}/generar", json=nueva, headers=admin_headers)
    asig = client.get(f"/matriz/asignaciones?desde={nueva['desde']}&hasta={nueva['hasta']}", headers=admin_headers).json()
    assert asig and all(a["trabajador"]["id"] != part.id for a in asig)


def test_desactivar_participante_exige_reemplazo(client, admin_headers, matriz, definir_password):
    titular, libre = matriz["ids"][0], matriz["ids"][4]
    client.post(
        f"/trabajadores/{titular}/usuario",
        json={"email": "tit@example.com", "cargo": "Analista"},
        headers=admin_headers,
    )
    uid = client.get("/usuarios?q=tit@", headers=admin_headers).json()[0]["id"]
    r = client.post(f"/usuarios/{uid}/desactivar", headers=admin_headers)
    assert r.status_code == 409 and r.json()["detail"]["codigo"] == "EN_MATRIZ"
    assert client.post(f"/usuarios/{uid}/desactivar?reemplazo_id={libre}", headers=admin_headers).status_code == 204


# ---------- Migración de roles de la Fase 1 ----------
def test_migracion_de_roles_legados(db_session):
    from app.db.init_db import consolidar_roles, migrar_roles_legados, seed_cargos, seed_roles

    viejo_admin, viejo_trab, desconocido = (
        Rol(nombre="Administrador"),
        Rol(nombre="Trabajador"),
        Rol(nombre="Superusuario legado"),
    )
    db_session.add_all([viejo_admin, viejo_trab, desconocido])
    t = Trabajador(documento="9", nombres="A", apellidos="B")
    db_session.add(t)
    db_session.flush()
    u = Usuario(username="u", email="u@example.com", password_hash="x", trabajador_id=t.id)
    u.roles.extend([viejo_admin, viejo_trab])
    db_session.add(u)
    db_session.commit()

    migrar_roles_legados(db_session)
    seed_roles(db_session)
    consolidar_roles(db_session)
    seed_cargos(db_session)
    seed_cargos(db_session)  # idempotente
    assert {r.nombre for r in db_session.query(Rol)} == {"Admin", "Usuario final"}
    assert [r.nombre for r in db_session.get(Usuario, u.id).roles] == ["Admin"]
    assert db_session.query(Cargo).count() == 3
