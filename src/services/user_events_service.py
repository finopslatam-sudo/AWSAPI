"""
USER EVENTS SERVICE
===================
Eventos del sistema relacionados con usuarios.
"""

import logging
from src.services.email_service import send_email
from src.services.email_templates import (
    build_user_welcome_email,
    build_plan_changed_email,
    build_account_deactivated_email,
    build_account_reactivated_email,
    build_password_changed_email,
    build_admin_reset_password_email,
    build_forgot_password_email,
    build_root_login_alert_email,
)

logger = logging.getLogger("user_events")


def safe_send_email(to: str, subject: str, body: str):
    try:
        send_email(to=to, subject=subject, body=body)
    except Exception:
        logger.exception("[EMAIL_FAILED] to=%s", to)

# -------------------------------------------------
# USER CREATED WITH PASSWORD
# -------------------------------------------------
def on_user_created_with_password(user, raw_password):
    logger.info(
        "[USER_CREATED_WITH_PASSWORD] user_id=%s email=%s",
        user.id,
        user.email,
    )

    safe_send_email(
        to=user.email,
        subject="Bienvenido a FinOpsLatam 🚀",
        body=build_user_welcome_email(
            "Usuario",
            user.email,
            raw_password,
        ),
    )

# -------------------------------------------------
# ACCOUNT DESACTIVED
# -------------------------------------------------
def on_user_deactivated(user):
    safe_send_email(
        to=user.email,
        subject="Tu cuenta ha sido desactivada 🔒 | FinOpsLatam",
        body=build_account_deactivated_email("Usuario"),
    )

# -------------------------------------------------
# ACCOUNT REACTIVED
# -------------------------------------------------
def on_user_reactivated(user):
    safe_send_email(
        to=user.email,
        subject="Tu cuenta ha sido reactivada 🔓 | FinOpsLatam",
        body=build_account_reactivated_email("Usuario"),
    )

# -------------------------------------------------
# PASSWORD ADMIN RESET PASSWORD
# -------------------------------------------------
def on_admin_reset_password(user, temp_password):
    safe_send_email(
        to=user.email,
        subject="Tu contraseña fue restablecida | FinOpsLatam",
        body=build_admin_reset_password_email(
            "Usuario",
            user.email,
            temp_password,
        ),
    )

# -------------------------------------------------
# PASSWORD RESET PASSWORD
# -------------------------------------------------
def on_password_changed(user):
    safe_send_email(
        to=user.email,
        subject="Tu contraseña ha sido actualizada 🔐 | FinOpsLatam",
        body=build_password_changed_email("Usuario"),
    )

# -------------------------------------------------
# PLAN CHANGE
# -------------------------------------------------
def on_user_plan_changed(user, old_plan, new_plan):
    safe_send_email(
        to=user.email,
        subject="Tu plan ha sido actualizado 📦 | FinOpsLatam",
        body=build_plan_changed_email(
            "Usuario",
            old_plan.name if old_plan else "Sin plan",
            new_plan.name,
        ),
    )

# -------------------------------------------------
# ALERT ROOT LOGIN
# -------------------------------------------------
def on_root_login(user, ip):
    safe_send_email(
        to=user.email,
        subject="⚠️ Inicio de sesión ROOT detectado | FinOpsLatam",
        body=build_root_login_alert_email(
            "Usuario",
            user.email,
            ip,
        ),
    )

# -------------------------------------------------
# FORGOT PASSWORD
# -------------------------------------------------
def on_forgot_password(user, temp_password):
    safe_send_email(
        to=user.email,
        subject="Recuperación de acceso | FinOpsLatam",
        body=build_forgot_password_email(
            "Usuario",
            user.email,
            temp_password,
        ),
    )
