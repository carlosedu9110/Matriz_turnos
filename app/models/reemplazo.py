"""Modelo de Reemplazo: un trabajador cubre a otro durante un periodo (y opcionalmente un turno)."""
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Reemplazo(Base):
    __tablename__ = "reemplazos"
    __table_args__ = (
        CheckConstraint("fecha_fin >= fecha_inicio", name="ck_reemplazo_fechas"),
        CheckConstraint("trabajador_ausente_id <> trabajador_reemplazo_id", name="ck_reemplazo_distintos"),
        Index("ix_reemplazo_reemplazo_fechas", "trabajador_reemplazo_id", "fecha_inicio", "fecha_fin"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trabajador_ausente_id: Mapped[int] = mapped_column(
        ForeignKey("trabajadores.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    trabajador_reemplazo_id: Mapped[int] = mapped_column(
        ForeignKey("trabajadores.id", ondelete="RESTRICT"), nullable=False
    )
    tipo_turno_id: Mapped[int | None] = mapped_column(
        ForeignKey("tipos_turno.id", ondelete="SET NULL"), nullable=True
    )
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    trabajador_ausente: Mapped["Trabajador"] = relationship(foreign_keys=[trabajador_ausente_id])
    trabajador_reemplazo: Mapped["Trabajador"] = relationship(foreign_keys=[trabajador_reemplazo_id])
    tipo_turno: Mapped["TipoTurno"] = relationship()

    def __repr__(self) -> str:
        return f"<Reemplazo id={self.id} {self.trabajador_ausente_id}->{self.trabajador_reemplazo_id}>"
