"""Pruebas de modelos ORM: relaciones y restricciones de unicidad."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Area, Cargo, TipoTurno, Trabajador, Usuario
from datetime import time


def test_area_cargo_trabajador_relationship(db_session):
    area = Area(nombre="Operaciones")
    cargo = Cargo(nombre="Analista", area=area)
    trabajador = Trabajador(documento="1", nombres="Luis", apellidos="Gómez", area=area, cargo=cargo)
    db_session.add_all([area, cargo, trabajador])
    db_session.commit()

    assert trabajador.area.nombre == "Operaciones"
    assert trabajador.cargo.nombre == "Analista"
    assert cargo in area.cargos


def test_trabajador_documento_unico(db_session):
    db_session.add(Trabajador(documento="dup", nombres="A", apellidos="B"))
    db_session.commit()

    db_session.add(Trabajador(documento="dup", nombres="C", apellidos="D"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_usuario_username_y_email_unicos(db_session):
    trabajador1 = Trabajador(documento="u1", nombres="A", apellidos="B")
    trabajador2 = Trabajador(documento="u2", nombres="C", apellidos="D")
    db_session.add_all([trabajador1, trabajador2])
    db_session.flush()

    db_session.add(
        Usuario(username="juan", email="juan@example.com", password_hash="x", trabajador_id=trabajador1.id)
    )
    db_session.commit()

    db_session.add(
        Usuario(username="juan", email="otro@example.com", password_hash="x", trabajador_id=trabajador2.id)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_usuario_roles_many_to_many(db_session, admin_role, worker_role):
    trabajador = Trabajador(documento="u3", nombres="Ana", apellidos="Ruiz")
    db_session.add(trabajador)
    db_session.flush()

    usuario = Usuario(
        username="ana", email="ana@example.com", password_hash="x", trabajador_id=trabajador.id
    )
    usuario.roles.extend([admin_role, worker_role])
    db_session.add(usuario)
    db_session.commit()

    assert {r.nombre for r in usuario.roles} == {"Administrador", "Trabajador"}
    assert usuario in admin_role.usuarios


def test_tipo_turno_creation(db_session):
    turno = TipoTurno(nombre="Diurno", hora_inicio=time(7, 0), hora_fin=time(15, 0))
    db_session.add(turno)
    db_session.commit()

    assert turno.id is not None
    assert turno.hora_inicio == time(7, 0)
