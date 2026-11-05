"""Utilidades compartidas para servicios/routers CRUD."""
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def get_or_404(db: Session, model, obj_id: int, nombre: str):
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{nombre} no encontrado")
    return obj


def commit_or_409(db: Session, detalle: str = "Ya existe un registro con esos datos únicos") -> None:
    """Confirma la transacción; ante violación de unicidad/FK responde 409."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detalle) from exc
