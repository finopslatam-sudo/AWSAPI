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
    logger.info(f"[USER_DEACTIVATED] user_id={user.id} email={user.email}")

    send_email(
        to=user.email,
        subject="Tu cuenta ha sido desactivada 🔒 | FinOpsLatam",
        body=build_account_deactivated_email(user.contact_name),
    )

    logger.info("[USER_DEACTIVATED] correo enviado")


def on_user_reactivated(user):
    logger.info(f"[USER_REACTIVATED] user_id={user.id} email={user.email}")

    send_email(
        to=user.email,
        subject="Tu cuenta ha sido reactivada 🔓 | FinOpsLatam",
        body=build_account_reactivated_email(user.contact_name),
    )

    logger.info("[USER_REACTIVATED] correo enviado")


def on_admin_reset_password(user, temp_password):
    logger.info(f"[ADMIN_RESET_PASSWORD] user_id={user.id} email={user.email}")

    body = build_admin_reset_password_email(
        user.contact_name,
        user.email,
        temp_password,
    )

    logger.info("[ADMIN_RESET_PASSWORD] cuerpo del correo construido")

    send_email(
        to=user.email,
        subject="Tu contraseña fue restablecida | FinOpsLatam",
        body=body,
    )

    logger.info("[ADMIN_RESET_PASSWORD] send_email ejecutado")


def on_password_changed(user):
    logger.info(f"[PASSWORD_CHANGED] user_id={user.id} email={user.email}")

    send_email(
        to=user.email,
        subject="Tu contraseña ha sido actualizada 🔐 | FinOpsLatam",
        body=build_password_changed_email(user.contact_name),
    )

    logger.info("[PASSWORD_CHANGED] correo enviado")


def on_user_plan_changed(user, old_plan, new_plan):
    old_name = old_plan.name if old_plan else "Sin plan"

    logger.info(
        f"[PLAN_CHANGED] user_id={user.id} email={user.email} "
        f"old_plan={old_name} new_plan={new_plan.name}"
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

    logger.info("[PLAN_CHANGED] correo enviado")


def on_root_login(user, ip):
    """
    Evento crítico: login con cuenta ROOT
    """
    logger.warning(f"[ROOT_LOGIN] user_id={user.id} email={user.email} ip={ip}")

    send_email(
        to=user.email,
        subject="⚠️ Inicio de sesión ROOT detectado | FinOpsLatam",
        body=build_root_login_alert_email(
            user.contact_name,
            user.email,
            ip,
        ),
    )

    logger.info("[ROOT_LOGIN] correo enviado")


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
