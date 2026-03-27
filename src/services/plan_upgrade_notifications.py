"""
Plan Upgrade Notifications
===========================
Lógica de notificaciones in-app y email para solicitudes de upgrade de plan.
"""

from src.models.user import User
from src.models.notification import Notification
from src.models.database import db
from src.services.email_service import send_email
from src.services.email_templates import build_plan_changed_email, build_plan_upgrade_rejected_email


def notify_upgrade_approved(request_upgrade, current_plan, new_plan):
    """Envía email + notificaciones in-app al aprobar un upgrade."""
    user = User.query.get(request_upgrade.requested_by_user_id)
    if user:
        email_body = build_plan_changed_email(
            name=user.contact_name,
            old_plan_name=current_plan.name,
            new_plan_name=new_plan.name,
        )
        send_email(to=user.email, subject="FinOpsLatam — Plan actualizado", body=email_body)

    try:
        Notification.query.filter_by(
            type="plan_upgrade_requested", reference_id=request_upgrade.id,
        ).delete()
        client_users = User.query.filter_by(
            client_id=request_upgrade.client_id, is_active=True
        ).all()
        for cu in client_users:
            db.session.add(Notification(
                user_id=cu.id,
                type="plan_upgrade_approved",
                title="¡Tu plan fue actualizado!",
                message=f"Tu plan ha sido actualizado a {new_plan.name}. Ya puedes disfrutar de las nuevas funcionalidades.",
            ))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error en notificaciones de aprobación: {e}")


def notify_upgrade_rejected(request_upgrade):
    """Envía email + notificaciones in-app al rechazar un upgrade."""
    user = User.query.get(request_upgrade.requested_by_user_id)
    if user:
        email_body = build_plan_upgrade_rejected_email(
            name=user.contact_name, plan_name=request_upgrade.requested_plan,
        )
        send_email(
            to=user.email,
            subject="FinOpsLatam — Solicitud de upgrade rechazada",
            body=email_body,
        )

    try:
        Notification.query.filter_by(
            type="plan_upgrade_requested", reference_id=request_upgrade.id,
        ).delete()
        plan_name = request_upgrade.requested_plan
        client_users = User.query.filter_by(
            client_id=request_upgrade.client_id, is_active=True
        ).all()
        for cu in client_users:
            db.session.add(Notification(
                user_id=cu.id,
                type="plan_upgrade_rejected",
                title="Solicitud de upgrade rechazada",
                message=f"Tu solicitud para cambiar al plan {plan_name} no fue aprobada. Contáctanos para más información.",
            ))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error en notificaciones de rechazo: {e}")
