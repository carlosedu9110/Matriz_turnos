"""Modelo de Area (unidad organizacional a la que pertenecen trabajadores/cargos)."""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Area(Base):
    __tablename__ = "areas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)

    cargos: Mapped[list["Cargo"]] = relationship(back_populates="area")
    trabajadores: Mapped[list["Trabajador"]] = relationship(back_populates="area")

    def __repr__(self) -> str:
        return f"<Area id={self.id} nombre={self.nombre!r}>"
