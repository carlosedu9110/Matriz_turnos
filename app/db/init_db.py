"""Script para crear el esquema inicial y sembrar datos base (roles, admin).

Uso:
    python -m app.db.init_db
"""
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import Rol, Trabajador, Usuario  # noqa: F401 (necesarios para metadata)

ROLES_BASE = ["Administrador", "Trabajador"]


def create_schema() -> None:
    """Crea todas las tablas definidas en los modelos si no existen."""
    Base.metadata.create_all(bind=engine)


def seed_roles(db: Session) -> None:
    """Crea los roles base si no existen."""
    for nombre in ROLES_BASE:
        if not db.query(Rol).filter(Rol.nombre == nombre).first():
            db.add(Rol(nombre=nombre))
    db.commit()


def seed_admin_user(db: Session) -> None:
    """Crea un trabajador/usuario administrador inicial si no existe ningún usuario."""
    if db.query(Usuario).count() > 0:
        return

    admin_rol = db.query(Rol).filter(Rol.nombre == "Administrador").first()
    trabajador = Trabajador(
        documento="00000000",
        nombres="Administrador",
        apellidos="Sistema",
    )
    db.add(trabajador)
    db.flush()

    usuario = Usuario(
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("Admin123!"),
        trabajador_id=trabajador.id,
    )
    if admin_rol:
        usuario.roles.append(admin_rol)
    db.add(usuario)
    db.commit()


def main() -> None:
    create_schema()
    db = SessionLocal()
    try:
        seed_roles(db)
        seed_admin_user(db)
    finally:
        db.close()
    print("Esquema creado y datos base sembrados correctamente.")


if __name__ == "__main__":
    main()
