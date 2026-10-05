"""Esquemas de Trabajador."""
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.catalogos import AreaOut, CargoOut


class UsuarioCreate(BaseModel):
    """Credenciales opcionales para dar acceso al sistema al crear un trabajador."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    rol: str = "Trabajador"


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
    area: AreaOut | None = None
    cargo: CargoOut | None = None
