"""Esquemas de catálogos: Area, Cargo y TipoTurno."""
from datetime import time

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AreaCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: str | None = Field(None, max_length=255)


class AreaUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=100)
    descripcion: str | None = Field(None, max_length=255)
    activo: bool | None = None


class AreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None = None
    activo: bool


class CargoCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: str | None = Field(None, max_length=255)
    area_id: int | None = None


class CargoUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=100)
    descripcion: str | None = Field(None, max_length=255)
    area_id: int | None = None
    activo: bool | None = None


class CargoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None = None
    area_id: int | None = None
    activo: bool


class TipoTurnoCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=50)
    hora_inicio: time
    hora_fin: time
    descripcion: str | None = Field(None, max_length=255)
    color: str | None = Field(None, max_length=20)

    @model_validator(mode="after")
    def _horas_distintas(self):
        if self.hora_inicio == self.hora_fin:
            raise ValueError("hora_inicio y hora_fin no pueden ser iguales")
        return self


class TipoTurnoUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=50)
    hora_inicio: time | None = None
    hora_fin: time | None = None
    descripcion: str | None = Field(None, max_length=255)
    color: str | None = Field(None, max_length=20)
    activo: bool | None = None


class TipoTurnoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    hora_inicio: time
    hora_fin: time
    descripcion: str | None = None
    color: str | None = None
    activo: bool
