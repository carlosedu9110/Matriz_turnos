"""Modelo de Trabajador (información laboral/personal, independiente de credenciales de acceso)."""
from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Trabajador(Base):
    __tablename__ = "trabajadores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    documento: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(100), nullable=False)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_ingreso: Mapped[date | None] = mapped_column(Date, nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)

    area_id: Mapped[int | None] = mapped_column(ForeignKey("areas.id", ondelete="SET NULL"), nullable=True)
    cargo_id: Mapped[int | None] = mapped_column(ForeignKey("cargos.id", ondelete="SET NULL"), nullable=True)

    activo: Mapped[bool] = mapped_column(default=True, nullable=False)

    area: Mapped["Area"] = relationship(back_populates="trabajadores")
    cargo: Mapped["Cargo"] = relationship(back_populates="trabajadores")
    usuario: Mapped["Usuario"] = relationship(
        back_populates="trabajador", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Trabajador id={self.id} documento={self.documento!r}>"
