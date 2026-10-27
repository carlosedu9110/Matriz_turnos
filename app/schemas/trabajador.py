"""Esquemas de Trabajador."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.catalogos import AreaOut, CargoOut

CargoUsuario = Literal["Analista", "Especialista", "Admin"]

class UsuarioCreate(BaseModel):
    """Acceso al sistema: el usuario define su propia contraseña con el enlace que recibe por correo."""

    email: EmailStr
    rol: Literal["Admin", "Usuario final"] = "Usuario final"
    cargo: CargoUsuario | None = None


class TrabajadorCreate(BaseModel):
    documento: str = Field(..., min_length=1, max_length=30)
    nombres: str = Field(..., min_length=1, max_length=100)
    apellidos: str = Field(..., min_length=1, max_length=100)
    fecha_nacimiento: date | None = None
    fecha_ingreso: date | None = None
    telefono: str | None = Field(None, max_length=30)
    area_id: int | None = None
    cargo_id: int | None = None
    usuario: UsuarioCreate | None = None


class TrabajadorUpdate(BaseModel):
    documento: str | None = Field(None, min_length=1, max_length=30)
    nombres: str | None = Field(None, min_length=1, max_length=100)
    apellidos: str | None = Field(None, min_length=1, max_length=100)
    fecha_nacimiento: date | None = None
    fecha_ingreso: date | None = None
    telefono: str | None = Field(None, max_length=30)
    area_id: int | None = None
    cargo_id: int | None = None
    activo: bool | None = None


class TrabajadorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    documento: str
    nombres: str
    apellidos: str
    fecha_nacimiento: date | None = None
    fecha_ingreso: date | None = None
    telefono: str | None = None
    activo: bool
    tiene_usuario: bool = False
    usuario_id: int | None = None
    email: str | None = None
    rol: str | None = None
    area: AreaOut | None = None
    cargo: CargoOut | None = None

class PosicionMatriz(BaseModel):
    ciclo_id: int
    ciclo_codigo: str
    ciclo_nombre: str
    rol: str
    fase: int
    titular: str | None = None


class ImpactoOut(BaseModel):
    en_matriz: bool
    posiciones: list[PosicionMatriz]
    asignaciones_futuras: int
    reemplazos_activos: int
