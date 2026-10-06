"""Esquemas de Reemplazo."""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.catalogos import TipoTurnoOut
from app.schemas.trabajador import TrabajadorOut


class ReemplazoCreate(BaseModel):
    trabajador_ausente_id: int
    trabajador_reemplazo_id: int
    tipo_turno_id: int | None = None
    fecha_inicio: date
    fecha_fin: date
    motivo: str | None = Field(None, max_length=255)

    @model_validator(mode="after")
    def _validar(self):
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser anterior a fecha_inicio")
        if self.trabajador_ausente_id == self.trabajador_reemplazo_id:
            raise ValueError("El trabajador que reemplaza debe ser distinto del ausente")
        return self


class ReemplazoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha_inicio: date
    fecha_fin: date
    motivo: str | None = None
    activo: bool
    trabajador_ausente: TrabajadorOut
    trabajador_reemplazo: TrabajadorOut
    tipo_turno: TipoTurnoOut | None = None
