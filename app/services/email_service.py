"""Envío de correos (invitaciones y recuperación de contraseña).

Backends (EMAIL_BACKEND): `console` (desarrollo: imprime el correo en el log del servidor),
`smtp` (producción) y `memory` (pruebas: guarda en `outbox`).
"""
import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("matriz.email")
outbox: list[dict] = []


def send_email(to: str, subject: str, body: str) -> bool:
    """Devuelve True si el correo se entregó al backend configurado; nunca lanza excepciones."""
    backend = settings.email_backend
    try:
        if backend == "memory":
            outbox.append({"to": to, "subject": subject, "body": body})
        elif backend == "smtp":
            msg = EmailMessage()
            msg["From"], msg["To"], msg["Subject"] = settings.smtp_from, to, subject
            msg.set_content(body)
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                if settings.smtp_starttls:
                    smtp.starttls()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
        else:
            logger.warning("CORREO (modo consola)\nPara: %s\nAsunto: %s\n%s", to, subject, body)
            print(f"\n=== CORREO (modo consola) ===\nPara: {to}\nAsunto: {subject}\n{body}\n=============================\n")
        return True
    except Exception:  # noqa: BLE001 - un fallo de correo no debe romper la operación principal
        logger.exception("No se pudo enviar el correo a %s", to)
        return False


def _enlace(token: str) -> str:
    # El fragmento no viaja al servidor HTTP ni aparece en sus access logs.
    return f"{settings.frontend_base_url.rstrip('/')}/app/#reset={token}"


def send_invitation(to: str, nombres: str, token: str) -> bool:
    return send_email(
        to,
        "Bienvenido a Matriz de turnos: define tu contraseña",
        f"Hola {nombres},\n\nSe creó tu cuenta en Matriz de turnos. Define tu contraseña en este enlace "
        f"(vence en {settings.invite_token_expire_hours} horas):\n{_enlace(token)}\n\n"
        "Nadie más conoce tu contraseña. Si no esperabas este correo, ignóralo.",
    )


def send_password_reset(to: str, nombres: str, token: str) -> bool:
    return send_email(
        to,
        "Recuperación de contraseña - Matriz de turnos",
        f"Hola {nombres},\n\nRecibimos una solicitud para restablecer tu contraseña. Usa este enlace "
        f"(vence en {settings.reset_token_expire_minutes} minutos y solo sirve una vez):\n{_enlace(token)}\n\n"
        "Si no fuiste tú, ignora este correo: tu contraseña no cambiará.",
    )
