"""Contratos API de vacaciones."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator



class PersonaVacacion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombres: str
    apellidos: str


EstadoVacacion = Literal["pendiente", "aprobada", "rechazada", "cancelada"]


class VacacionCreate(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    motivo: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def _fechas_validas(self):
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser anterior a fecha_inicio")
        if (self.fecha_fin - self.fecha_inicio).days > 365:
            raise ValueError("El periodo de vacaciones no puede superar un año")
        return self


class VacacionDecision(BaseModel):
    estado: Literal["aprobada", "rechazada"]
    nota_admin: str | None = Field(None, max_length=2000)
    reemplazante_id: int | None = None


class VacacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trabajador_id: int
    trabajador: PersonaVacacion
    fecha_inicio: date
    fecha_fin: date
    motivo: str | None = None
    estado: EstadoVacacion
    nota_admin: str | None = None
    reemplazo_id: int | None = None
    creado_en: datetime


class VacacionMatriz(BaseModel):
    id: int
    trabajador_id: int
    trabajador: PersonaVacacion
    fecha_inicio: date
    fecha_fin: date
    estado: EstadoVacacion
    reemplazante: PersonaVacacion | None = None
