"""Endpoint de healthcheck básico."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Verifica que el servicio esté en ejecución."""
    return {"status": "ok"}
