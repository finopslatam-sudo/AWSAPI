"""
USER EVENTS SERVICE
===================

Orquestador de eventos del sistema relacionados con usuarios.

Responsabilidades:
- Registrar eventos relevantes (auditoría básica)
- Disparar notificaciones por correo
- NO contiene lógica de negocio
- NO rompe flujos si el email falla
"""

import logging

from src.services.email_service import send_email
from src.services.email_templates import (
    build_plan_changed_email,
    build_account_deactivated_email,
    build_account_reactivated_email,
    build_password_changed_email,
    build_admin_reset_password_email,
    build_forgot_password_email,
    build_root_login_alert_email,
)

logger = logging.getLogger("user_events")


# -------------------------------------------------
# Eventos de usuario
# -------------------------------------------------
def on_user_created_with_password(user, raw_password):
    """
    Evento: usuario cliente creado con password explícita.
    Envía correo de bienvenida con credenciales.
    """

    logger.info(
        "[USER_CREATED_WITH_PASSWORD] user_id=%s email=%s",
        user.id,
        user.email,
    )

    send_email(
        to=user.email,
        subject="Bienvenido a FinOpsLatam 🚀",
        body=build_admin_reset_password_email(
            user.contact_name,
            user.email,
            raw_password,
        ),
    )

def on_user_deactivated(user):
    logger.info(
        "[USER_DEACTIVATED] user_id=%s email=%s",
        user.id,
        user.email,
    )

    send_email(
        to=user.email,
        subject="Tu cuenta ha sido desactivada 🔒 | FinOpsLatam",
        body=build_account_deactivated_email(user.contact_name),
    )


def on_user_reactivated(user):
    logger.info(
        "[USER_REACTIVATED] user_id=%s email=%s",
        user.id,
        user.email,
    )

    send_email(
        to=user.email,
        subject="Tu cuenta ha sido reactivada 🔓 | FinOpsLatam",
        body=build_account_reactivated_email(user.contact_name),
    )


def on_admin_reset_password(user, temp_password):
    logger.warning(
        "[ADMIN_RESET_PASSWORD] user_id=%s email=%s",
        user.id,
        user.email,
    )

    send_email(
        to=user.email,
        subject="Tu contraseña fue restablecida | FinOpsLatam",
        body=build_admin_reset_password_email(
            user.contact_name,
            user.email,
            temp_password,
        ),
    )


def on_password_changed(user):
    logger.info(
        "[PASSWORD_CHANGED] user_id=%s email=%s",
        user.id,
        user.email,
    )

    send_email(
        to=user.email,
        subject="Tu contraseña ha sido actualizada 🔐 | FinOpsLatam",
        body=build_password_changed_email(user.contact_name),
    )


def on_user_plan_changed(user, old_plan, new_plan):
    old_name = old_plan.name if old_plan else "Sin plan"

    logger.info(
        "[PLAN_CHANGED] user_id=%s email=%s old_plan=%s new_plan=%s",
        user.id,
        user.email,
        old_name,
        new_plan.name,
    )

    send_email(
        to=user.email,
        subject="Tu plan ha sido actualizado 📦 | FinOpsLatam",
        body=build_plan_changed_email(
            user.contact_name,
            old_name,
            new_plan.name,
        ),
    )


def on_root_login(user, ip):
    """
    Evento crítico: inicio de sesión con cuenta ROOT.
    """
    logger.warning(
        "[ROOT_LOGIN] user_id=%s email=%s ip=%s",
        user.id,
        user.email,
        ip,
    )

    send_email(
        to=user.email,
        subject="⚠️ Inicio de sesión ROOT detectado | FinOpsLatam",
        body=build_root_login_alert_email(
            user.contact_name,
            user.email,
            ip,
        ),
    )


# -------------------------------------------------
# Forgot password
# -------------------------------------------------
def on_forgot_password(user, temp_password):
    logger.info(
        "[FORGOT_PASSWORD] user_id=%s email=%s",
        user.id,
        user.email,
    )

    send_email(
        to=user.email,
        subject="Recuperación de acceso | FinOpsLatam",
        body=build_forgot_password_email(
            user.contact_name,
            user.email,
            temp_password,
        ),
    )
