"""Endpoints de autenticación: login y usuario actual."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageOut,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.usuario import UsuarioOut
from app.services.acceso_service import MENSAJE_RECUPERACION, restablecer_password, solicitar_recuperacion
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


@router.post("/forgot-password", response_model=MessageOut)
def forgot_password(datos: ForgotPasswordRequest, db: Session = Depends(get_db)) -> MessageOut:
    """Envía el enlace de recuperación al correo de la cuenta. La respuesta es siempre la misma."""
    solicitar_recuperacion(db, datos.email)
    return MessageOut(mensaje=MENSAJE_RECUPERACION)


@router.post("/reset-password", response_model=MessageOut)
def reset_password(datos: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageOut:
    """Define una nueva contraseña con el enlace recibido por correo (un solo uso)."""
    restablecer_password(db, datos.token, datos.new_password)
    return MessageOut(mensaje="Contraseña actualizada. Ya puedes iniciar sesión.")

@router.post("/token", response_model=TokenResponse, include_in_schema=True)
def login_form(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> TokenResponse:
    """Login con formulario OAuth2; lo usa el botón Authorize de Swagger (/docs)."""
    return login(LoginRequest(username=form.username, password=form.password), db)
