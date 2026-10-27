"""Crea el esquema inicial y siembra los datos base (roles, cargos, tipos de turno, Admin inicial).

Uso:
    python -m app.db.init_db

Es idempotente y migra los roles de la Fase 1 (Administrador/Trabajador → Admin/Usuario final).
Variables opcionales para el primer Admin: ADMIN_EMAIL y ADMIN_PASSWORD.
"""
from sqlalchemy.orm import Session

from app.config import settings
from app.core.roles import CARGO_ADMIN, CARGOS, ROL_ADMIN, ROL_USUARIO_FINAL, ROLES, ROLES_LEGADOS
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import Cargo, Rol, Trabajador, Usuario  # noqa: F401 (necesarios para metadata)
from app.services.matriz_service import sembrar_tipos_turno


def create_schema() -> None:
    """Crea todas las tablas definidas en los modelos si no existen."""
    Base.metadata.create_all(bind=engine)


def migrar_roles_legados(db: Session) -> None:
    """Renombra Administrador→Admin y Trabajador→Usuario final conservando las asignaciones."""
    for viejo, nuevo in ROLES_LEGADOS.items():
        rol_viejo = db.query(Rol).filter(Rol.nombre == viejo).first()
        if rol_viejo is None:
            continue
        rol_nuevo = db.query(Rol).filter(Rol.nombre == nuevo).first()
        if rol_nuevo is None:
            rol_viejo.nombre = nuevo
        else:
            for u in list(rol_viejo.usuarios):
                u.roles = [r for r in u.roles if r.id != rol_viejo.id]
                if rol_nuevo not in u.roles:
                    u.roles.append(rol_nuevo)
            db.flush()
            db.delete(rol_viejo)
        db.flush()
    db.commit()


def seed_roles(db: Session) -> None:
    """Crea los dos roles del sistema si no existen."""
    for nombre in ROLES:
        if not db.query(Rol).filter(Rol.nombre == nombre).first():
            db.add(Rol(nombre=nombre))
    db.commit()


def consolidar_roles(db: Session) -> None:
    """Cada cuenta recibe un solo rol; si hay legado múltiple, conserva Admin por seguridad."""
    admin = db.query(Rol).filter(Rol.nombre == ROL_ADMIN).one()
    usuario_final = db.query(Rol).filter(Rol.nombre == ROL_USUARIO_FINAL).one()
    for usuario in db.query(Usuario).all():
        nombres = {rol.nombre for rol in usuario.roles}
        usuario.roles = [admin if ROL_ADMIN in nombres else usuario_final]
    for rol in db.query(Rol).filter(~Rol.nombre.in_(ROLES)).all():
        db.delete(rol)
    db.commit()


def seed_cargos(db: Session) -> None:
    """Crea los cargos disponibles (Analista, Especialista, Admin)."""
    for nombre in CARGOS:
        cargo = db.query(Cargo).filter(Cargo.nombre == nombre).first()
        if cargo is None:
            db.add(Cargo(nombre=nombre))
        elif not cargo.activo:
            cargo.activo = True
    db.commit()


def seed_admin_user(db: Session) -> None:
    """Crea el Admin inicial si no existe ningún usuario; si ya existe, solo completa su cargo."""
    cargo_admin = db.query(Cargo).filter(Cargo.nombre == CARGO_ADMIN).first()
    if db.query(Usuario).count() > 0:
        for t in db.query(Trabajador).join(Usuario).join(Usuario.roles).filter(
            Rol.nombre == ROL_ADMIN, Trabajador.cargo_id.is_(None), Trabajador.documento == "00000000"
        ):
            t.cargo = cargo_admin
        db.commit()
        return

    trabajador = Trabajador(documento="00000000", nombres="Administrador", apellidos="Sistema", cargo=cargo_admin)
    db.add(trabajador)
    db.flush()
    usuario = Usuario(
        username="admin",
        email=settings.admin_email.strip().lower(),
        password_hash=hash_password(settings.admin_password),
        trabajador_id=trabajador.id,
    )
    usuario.roles.append(db.query(Rol).filter(Rol.nombre == ROL_ADMIN).one())
    db.add(usuario)
    db.commit()


def main() -> None:
    create_schema()
    db = SessionLocal()
    try:
        migrar_roles_legados(db)
        seed_roles(db)
        consolidar_roles(db)
        seed_cargos(db)
        seed_admin_user(db)
        sembrar_tipos_turno(db)
    finally:
        db.close()
    print("Esquema creado y datos base sembrados correctamente.")


if __name__ == "__main__":
    main()
