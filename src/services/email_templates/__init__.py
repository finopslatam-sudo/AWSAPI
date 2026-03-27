"""
email_templates package
=======================
Re-exporta todas las plantillas para mantener compatibilidad con imports existentes.
"""

from src.services.email_templates.auth import (
    build_forgot_password_email,
    build_account_deactivated_email,
    build_account_reactivated_email,
    build_password_changed_email,
    build_admin_reset_password_email,
    build_root_login_alert_email,
    build_user_welcome_email,
)
from src.services.email_templates.alerts import build_alert_fired_email
from src.services.email_templates.upgrades import (
    build_plan_changed_email,
    build_plan_upgrade_request_received_email,
    build_plan_upgrade_rejected_email,
    build_internal_plan_upgrade_alert,
)

__all__ = [
    "build_forgot_password_email",
    "build_account_deactivated_email",
    "build_account_reactivated_email",
    "build_password_changed_email",
    "build_admin_reset_password_email",
    "build_root_login_alert_email",
    "build_user_welcome_email",
    "build_alert_fired_email",
    "build_plan_changed_email",
    "build_plan_upgrade_request_received_email",
    "build_plan_upgrade_rejected_email",
    "build_internal_plan_upgrade_alert",
]
