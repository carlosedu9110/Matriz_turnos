"""Tabla de asociación muchos-a-muchos entre Usuario y Rol."""
from sqlalchemy import Column, ForeignKey, Table

from app.db.session import Base

usuario_rol = Table(
    "usuario_rol",
    Base.metadata,
    Column("usuario_id", ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
    Column("rol_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)
