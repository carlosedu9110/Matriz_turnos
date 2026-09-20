"""Endpoints de autenticación: login y usuario actual."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.usuario import UsuarioOut
from app.services.auth_service import authenticate_user, build_tokens_for_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Autentica al usuario con username/password y devuelve tokens JWT."""
    usuario = authenticate_user(db, credentials.username, credentials.password)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token, refresh_token = build_tokens_for_user(usuario)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UsuarioOut)
def read_current_user(current_user: Usuario = Depends(get_current_active_user)) -> Usuario:
    """Devuelve la información del usuario autenticado."""
    return current_user
