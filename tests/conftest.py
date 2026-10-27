"""Fixtures compartidos de pytest: BD SQLite en memoria y cliente de pruebas de FastAPI."""
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.roles import CARGOS, ROL_ADMIN, ROL_USUARIO_FINAL
from app.core.security import hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models import Cargo, Rol, Trabajador, Usuario
from app.services import email_service

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def correo_en_memoria(monkeypatch):
    """Los correos no se envían: quedan en email_service.outbox."""
    monkeypatch.setattr(settings, "email_backend", "memory")
    email_service.outbox.clear()
    yield email_service.outbox
    email_service.outbox.clear()


@pytest.fixture()
def db_session():
    """Crea el esquema en una BD SQLite en memoria por cada test y lo destruye al final."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    """Cliente de pruebas de FastAPI con la dependencia get_db sobreescrita hacia SQLite."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_role(db_session):
    rol = Rol(nombre=ROL_ADMIN, descripcion="Gestiona usuarios, turnos y reemplazos")
    db_session.add(rol)
    db_session.commit()
    db_session.refresh(rol)
    return rol


@pytest.fixture()
def worker_role(db_session):
    rol = Rol(nombre=ROL_USUARIO_FINAL, descripcion="Consulta su información y sus turnos")
    db_session.add(rol)
    db_session.commit()
    db_session.refresh(rol)
    return rol


@pytest.fixture()
def cargos(db_session):
    filas = [Cargo(nombre=n) for n in CARGOS]
    db_session.add_all(filas)
    db_session.commit()
    return {c.nombre: c for c in filas}


@pytest.fixture()
def sample_user(db_session, admin_role):
    """Trabajador + Usuario activo con rol Admin y contraseña conocida (solo para pruebas)."""
    trabajador = Trabajador(documento="123456789", nombres="Ana", apellidos="Pérez")
    db_session.add(trabajador)
    db_session.flush()

    usuario = Usuario(
        username="apere",
        email="apere@example.com",
        password_hash=hash_password("Secret123!"),
        trabajador_id=trabajador.id,
    )
    usuario.roles.append(admin_role)
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(usuario)
    return usuario


@pytest.fixture()
def definir_password(client, correo_en_memoria):
    """Simula al usuario: toma el enlace más reciente enviado a `email` y define su contraseña."""

    def _definir(email: str, password: str):
        correos = [m for m in correo_en_memoria if m["to"] == email]
        assert correos, f"No se envió ningún correo a {email}"
        token = re.search(r"#reset=(\S+)", correos[-1]["body"]).group(1)
        return client.post("/auth/reset-password", json={"token": token, "new_password": password})

    return _definir
