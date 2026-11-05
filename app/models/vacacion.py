"""Solicitud de vacaciones de un trabajador, con aprobación administrativa."""
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Vacacion(Base):
    __tablename__ = "vacaciones"
    __table_args__ = (
        CheckConstraint("fecha_fin >= fecha_inicio", name="ck_vacacion_fechas"),
        CheckConstraint(
            "estado IN ('pendiente', 'aprobada', 'rechazada', 'cancelada')",
            name="ck_vacacion_estado",
        ),
        Index("ix_vacacion_trabajador_fechas", "trabajador_id", "fecha_inicio", "fecha_fin"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trabajador_id: Mapped[int] = mapped_column(
        ForeignKey("trabajadores.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente", index=True)
    nota_admin: Mapped[str | None] = mapped_column(Text, nullable=True)
    reemplazo_id: Mapped[int | None] = mapped_column(
        ForeignKey("reemplazos.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    trabajador: Mapped["Trabajador"] = relationship()
    reemplazo: Mapped["Reemplazo | None"] = relationship(back_populates="vacacion")
