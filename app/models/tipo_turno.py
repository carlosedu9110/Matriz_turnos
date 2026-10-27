"""Modelo de TipoTurno (plantillas de turno, ej. Diurno, Nocturno, Festivo)."""
from sqlalchemy import String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from datetime import time


class TipoTurno(Base):
    __tablename__ = "tipos_turno"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<TipoTurno id={self.id} nombre={self.nombre!r}>"
