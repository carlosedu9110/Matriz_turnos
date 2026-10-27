"""Esquemas relacionados con Usuario."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

CargoNombre = Literal["Analista", "Especialista", "Admin"]
RolNombre = Literal["Admin", "Usuario final"]


def _limpiar(v: str) -> str:
    v = " ".join(v.split())
    if not v:
        raise ValueError("No puede estar vacío")
    return v


class RolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class UsuarioOut(BaseModel):
    """Perfil propio (GET /auth/me)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    activo: bool
    nombres: str
    apellidos: str
    telefono: str | None = None
    cargo: str | None = None
    roles: list[RolOut] = Field(default_factory=list)


class UsuarioAdminOut(UsuarioOut):
    """Vista administrativa: añade el trabajador asociado. Nunca incluye contraseñas ni hashes."""

    trabajador_id: int


class UsuarioCrearOut(BaseModel):
    usuario: UsuarioAdminOut
    correo_enviado: bool
    mensaje: str


class UsuarioIn(BaseModel):
    nombres: str = Field(..., min_length=1, max_length=100)
    apellidos: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    telefono: str = Field(..., min_length=3, max_length=30)
    cargo: CargoNombre
    rol: RolNombre = "Usuario final"
    documento: str | None = Field(None, min_length=1, max_length=30)

    _limpio = field_validator("nombres", "apellidos", "telefono", mode="after")(_limpiar)


class UsuarioUpdate(BaseModel):
    nombres: str | None = Field(None, min_length=1, max_length=100)
    apellidos: str | None = Field(None, min_length=1, max_length=100)
    email: EmailStr | None = None
    telefono: str | None = Field(None, min_length=3, max_length=30)
    cargo: CargoNombre | None = None
    rol: RolNombre | None = None
    documento: str | None = Field(None, min_length=1, max_length=30)

    @field_validator("nombres", "apellidos", "telefono", mode="after")
    @classmethod
    def _opcional(cls, v):
        return None if v is None else _limpiar(v)
