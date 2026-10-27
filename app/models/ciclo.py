"""Modelos de la matriz de turnos: ciclo rotativo, plantilla semanal y asignaciones diarias."""
from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class CicloTurno(Base):
    """Matriz con ciclo rotativo de 4 semanas (`codigo`: matriz_analistas, matriz_especialistas, ...). `fecha_ancla` (lunes) es el inicio de la semana 1 de la fase 1."""

    __tablename__ = "ciclos_turno"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    fecha_ancla: Mapped[date] = mapped_column(Date, nullable=False)
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)

    participantes: Mapped[list["CicloParticipante"]] = relationship(
        back_populates="ciclo", cascade="all, delete-orphan", order_by="CicloParticipante.fase"
    )
    plantilla: Mapped[list["CicloPlantilla"]] = relationship(
        back_populates="ciclo", cascade="all, delete-orphan"
    )


class CicloParticipante(Base):
    """Persona titular del ciclo, con su fase (1-4) y su relevo (quien lo reemplaza)."""

    __tablename__ = "ciclo_participantes"
    __table_args__ = (
        UniqueConstraint("ciclo_id", "fase", name="uq_ciclo_fase"),
        UniqueConstraint("ciclo_id", "trabajador_id", name="uq_ciclo_trabajador"),
        CheckConstraint("fase BETWEEN 1 AND 4", name="ck_participante_fase"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ciclo_id: Mapped[int] = mapped_column(ForeignKey("ciclos_turno.id", ondelete="CASCADE"), nullable=False)
    trabajador_id: Mapped[int] = mapped_column(ForeignKey("trabajadores.id", ondelete="RESTRICT"), nullable=False)
    relevo_id: Mapped[int | None] = mapped_column(ForeignKey("trabajadores.id", ondelete="SET NULL"), nullable=True)
    fase: Mapped[int] = mapped_column(nullable=False)

    ciclo: Mapped[CicloTurno] = relationship(back_populates="participantes")
    trabajador: Mapped["Trabajador"] = relationship(foreign_keys=[trabajador_id])
    relevo: Mapped["Trabajador"] = relationship(foreign_keys=[relevo_id])


class CicloPlantilla(Base):
    """Qué turno trabaja una fase en cada (semana 1-4, día 0=lunes..6=domingo). Sin fila = descanso."""

    __tablename__ = "ciclo_plantilla"
    __table_args__ = (
        UniqueConstraint("ciclo_id", "semana", "dia_semana", name="uq_plantilla_dia"),
        CheckConstraint("semana BETWEEN 1 AND 4", name="ck_plantilla_semana"),
        CheckConstraint("dia_semana BETWEEN 0 AND 6", name="ck_plantilla_dia"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ciclo_id: Mapped[int] = mapped_column(ForeignKey("ciclos_turno.id", ondelete="CASCADE"), nullable=False)
    semana: Mapped[int] = mapped_column(nullable=False)
    dia_semana: Mapped[int] = mapped_column(nullable=False)
    tipo_turno_id: Mapped[int] = mapped_column(ForeignKey("tipos_turno.id", ondelete="RESTRICT"), nullable=False)

    ciclo: Mapped[CicloTurno] = relationship(back_populates="plantilla")
    tipo_turno: Mapped["TipoTurno"] = relationship()


class Asignacion(Base):
    """Turno de una persona en una fecha (el turno nocturno pertenece al día en que inicia)."""

    __tablename__ = "asignaciones"
    __table_args__ = (UniqueConstraint("trabajador_id", "fecha", name="uq_asignacion_trabajador_fecha"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trabajador_id: Mapped[int] = mapped_column(ForeignKey("trabajadores.id", ondelete="RESTRICT"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tipo_turno_id: Mapped[int] = mapped_column(ForeignKey("tipos_turno.id", ondelete="RESTRICT"), nullable=False)
    ciclo_id: Mapped[int | None] = mapped_column(ForeignKey("ciclos_turno.id", ondelete="SET NULL"), nullable=True)
    manual: Mapped[bool] = mapped_column(default=False, nullable=False)

    trabajador: Mapped["Trabajador"] = relationship()
    tipo_turno: Mapped["TipoTurno"] = relationship()
