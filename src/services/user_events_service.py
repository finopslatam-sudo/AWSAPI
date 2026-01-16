from flask import request
from src.services.email_service import send_email
from src.services.email_templates import build_plan_changed_email
from src.services.email_templates import build_root_login_alert_email
from src.services.email_templates import (
    build_account_deactivated_email,
    build_account_reactivated_email,
    build_admin_reset_password_email,
    build_password_changed_email,
)


def on_user_deactivated(user):
    send_email(
        to=user.email,
        subject="Tu cuenta ha sido desactivada 🔒 | FinOpsLatam",
        body=build_account_deactivated_email(user.contact_name)
    )


def on_user_reactivated(user):
    send_email(
        to=user.email,
        subject="Tu cuenta ha sido reactivada 🔓 | FinOpsLatam",
        body=build_account_reactivated_email(user.contact_name)
    )


def on_admin_reset_password(user, temp_password):
    send_email(
        to=user.email,
        subject="Tu contraseña fue restablecida | FinOpsLatam",
        body=build_admin_reset_password_email(
            user.contact_name,
            user.email,
            temp_password
        )
    )

def on_password_changed(user):
    send_email(
        to=user.email,
        subject="Tu contraseña ha sido actualizada 🔐 | FinOpsLatam",
        body=build_password_changed_email(user.contact_name)
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
            new_plan.name
        )
    )

def on_root_login(user):
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
            ip
        )
    )
