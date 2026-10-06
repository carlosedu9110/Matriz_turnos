"""Esquemas de la matriz de turnos."""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.catalogos import TipoTurnoOut


class ParticipanteIn(BaseModel):
    trabajador_id: int
    fase: int = Field(..., ge=1, le=4)
    relevo_id: int | None = None


class CicloCreate(BaseModel):
    codigo: str = Field(..., pattern=r"^[a-z0-9_]{3,50}$", description="Identificador, ej. matriz_analistas")
    nombre: str = Field(..., min_length=1, max_length=100)
    fecha_ancla: date = Field(..., description="Lunes en que inicia la semana 1 de la fase 1")
    participantes: list[ParticipanteIn] = Field(..., min_length=4, max_length=4)

    @model_validator(mode="after")
    def _validar(self):
        if self.fecha_ancla.weekday() != 0:
            raise ValueError("fecha_ancla debe ser un lunes")
        if sorted(p.fase for p in self.participantes) != [1, 2, 3, 4]:
            raise ValueError("Se requieren exactamente las fases 1, 2, 3 y 4")
        ids = [p.trabajador_id for p in self.participantes]
        if len(set(ids)) != 4:
            raise ValueError("Los 4 titulares deben ser personas distintas")
        relevos = [p.relevo_id for p in self.participantes if p.relevo_id is not None]
        if len(set(relevos)) != len(relevos) or set(relevos) & set(ids):
            raise ValueError("Los relevos deben ser distintos entre sí y no ser titulares")
        return self


class PersonaMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombres: str
    apellidos: str
    activo: bool = True


class ParticipanteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fase: int
    trabajador: PersonaMini
    relevo: PersonaMini | None = None


class PlantillaItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    semana: int
    dia_semana: int
    tipo_turno_id: int


class CicloOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    fecha_ancla: date
    activo: bool
    participantes: list[ParticipanteOut]
    plantilla: list[PlantillaItemOut]


class GenerarIn(BaseModel):
    desde: date
    hasta: date
    sobrescribir: bool = False

    @model_validator(mode="after")
    def _validar(self):
        if self.hasta < self.desde:
            raise ValueError("hasta no puede ser anterior a desde")
        if (self.hasta - self.desde).days > 366:
            raise ValueError("El rango máximo es de 366 días")
        return self


class GenerarOut(BaseModel):
    creadas: int
    actualizadas: int
    omitidas: int


class AsignacionManualIn(BaseModel):
    trabajador_id: int
    fecha: date
    tipo_turno_id: int


class CeldaOut(BaseModel):
    """Una persona trabajando un turno en una fecha. Si es cobertura, `titular` es a quien cubre."""

    asignacion_id: int
    fecha: date
    tipo_turno_id: int
    trabajador: PersonaMini
    es_reemplazo: bool = False
    titular: PersonaMini | None = None
    reemplazo_id: int | None = None
    manual: bool = False


class MatrizOut(BaseModel):
    desde: date
    hasta: date
    tipos_turno: list[TipoTurnoOut]
    celdas: list[CeldaOut]
    ciclo: CicloOut | None = None
