import logging
from flask import request

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

# -------------------------------------------------
# Logging
# -------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("user_events")

# -------------------------------------------------
# Eventos de usuario
# -------------------------------------------------
def on_user_deactivated(user):
    send_email(
        to=user.email,
        subject="Tu cuenta ha sido desactivada 🔒 | FinOpsLatam",
        body=build_account_deactivated_email(user.contact_name),
    )


def on_user_reactivated(user):
    send_email(
        to=user.email,
        subject="Tu cuenta ha sido reactivada 🔓 | FinOpsLatam",
        body=build_account_reactivated_email(user.contact_name),
    )


def on_admin_reset_password(user, temp_password):
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
    send_email(
        to=user.email,
        subject="Tu contraseña ha sido actualizada 🔐 | FinOpsLatam",
        body=build_password_changed_email(user.contact_name),
    )


def on_user_plan_changed(user, old_plan, new_plan):
    """
    Evento: cambio de plan (upgrade o downgrade)
    """
    if not old_plan or not new_plan:
        return

    send_email(
        to=user.email,
        subject="Tu plan ha sido actualizado 📦 | FinOpsLatam",
        body=build_plan_changed_email(
            user.contact_name,
            new_plan.name,
        ),
    )


def on_root_login(user, ip):
    """
    Evento crítico: login con cuenta ROOT
    """
    ip = request.remote_addr

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
    logger.info(f"[FORGOT_PASSWORD] evento iniciado user_id={user.id}")
    logger.info(f"[FORGOT_PASSWORD] email destino={user.email}")

    body = build_forgot_password_email(
        user.contact_name,
        user.email,
        temp_password,
    )

    logger.info("[FORGOT_PASSWORD] cuerpo del correo construido")

    send_email(
        to=user.email,
        subject="Recuperación de acceso | FinOpsLatam",
        body=body,
    )

    logger.info("[FORGOT_PASSWORD] send_email ejecutado")
