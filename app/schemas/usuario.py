"""Esquemas relacionados con Usuario."""
from pydantic import BaseModel, ConfigDict, EmailStr


class RolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    activo: bool
    roles: list[RolOut] = []
