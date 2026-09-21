"""Fixtures compartidos de pytest: BD SQLite en memoria y cliente de pruebas de FastAPI."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models import Cargo, Rol, Trabajador, Usuario

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
    rol = Rol(nombre="Administrador", descripcion="Rol con acceso total")
    db_session.add(rol)
    db_session.commit()
    db_session.refresh(rol)
    return rol


@pytest.fixture()
def worker_role(db_session):
    rol = Rol(nombre="Trabajador", descripcion="Rol estándar de trabajador")
    db_session.add(rol)
    db_session.commit()
    db_session.refresh(rol)
    return rol


@pytest.fixture()
def sample_user(db_session, admin_role):
    """Crea un Trabajador + Usuario activo con rol Administrador y contraseña conocida."""
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
