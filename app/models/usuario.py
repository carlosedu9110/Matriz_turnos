"""Modelo de Usuario (credenciales de acceso al sistema, ligadas 1-a-1 a un Trabajador)."""
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)

    trabajador_id: Mapped[int] = mapped_column(
        ForeignKey("trabajadores.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    trabajador: Mapped["Trabajador"] = relationship(back_populates="usuario")
    roles: Mapped[list["Rol"]] = relationship(secondary="usuario_rol", back_populates="usuarios")

    def __repr__(self) -> str:
        return f"<Usuario id={self.id} username={self.username!r}>"
