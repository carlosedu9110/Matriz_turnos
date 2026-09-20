"""Modelo de Rol (permisos/roles de autorización, ej. Administrador/Trabajador)."""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Rol(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)

    usuarios: Mapped[list["Usuario"]] = relationship(
        secondary="usuario_rol", back_populates="roles"
    )

    def __repr__(self) -> str:
        return f"<Rol id={self.id} nombre={self.nombre!r}>"
