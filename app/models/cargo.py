"""Modelo de Cargo (posición/rol laboral dentro de un Area)."""
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Cargo(Base):
    __tablename__ = "cargos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    area_id: Mapped[int | None] = mapped_column(ForeignKey("areas.id", ondelete="SET NULL"), nullable=True)
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)

    area: Mapped["Area"] = relationship(back_populates="cargos")
    trabajadores: Mapped[list["Trabajador"]] = relationship(back_populates="cargo")

    def __repr__(self) -> str:
        return f"<Cargo id={self.id} nombre={self.nombre!r}>"
