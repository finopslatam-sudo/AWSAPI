"""
WEBHOOKS ROUTES — PAYPAL
========================
Recibe eventos de PayPal y ejecuta la lógica post-pago.

Flujo para BILLING.SUBSCRIPTION.ACTIVATED:
  1. Verificar firma del webhook (PAYPAL_WEBHOOK_ID)
  2. Buscar Payment por paypal_subscription_id y actualizar status a 'active'
  3. Enviar email de bienvenida al cliente
  4. Enviar email de notificación a todos los staff (root/admin/support)
  5. Crear notificación in-app para cada usuario staff

SEGURIDAD:
  - Sin JWT (PayPal llama directamente)
  - Firma verificada con PAYPAL_WEBHOOK_ID via API de PayPal
  - Idempotencia: status 'active' previene reprocesamiento
"""

import logging
from flask import Blueprint, jsonify, request

from src.models.database import db
from src.models.payment import Payment
from src.models.user import User
from src.models.notification import Notification
from src.services.email_service import send_email
from src.services.email_templates import (
    build_payment_welcome_email,
    build_admin_new_payment_email,
)
from src.services.paypal_service import verify_webhook_signature

logger = logging.getLogger("webhooks")

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/api/webhooks")

_STAFF_ROLES = ("root", "admin", "support")


def _get_staff_users() -> list[User]:
    return User.query.filter(
        User.global_role.in_(_STAFF_ROLES),
        User.is_active == True,
    ).all()


def _notify_staff(message: str, title: str, ref_id: int) -> None:
    for staff in _get_staff_users():
        db.session.add(Notification(
            user_id=staff.id,
            type="new_subscription",
            title=title,
            message=message,
            reference_id=ref_id,
        ))


def _handle_subscription_activated(resource: dict) -> None:
    """Procesa BILLING.SUBSCRIPTION.ACTIVATED — activa el registro del pago."""
    subscription_id = resource.get("id", "")

    payment = Payment.query.filter_by(paypal_subscription_id=subscription_id).first()
    if not payment:
        logger.warning("Suscripción PayPal no encontrada en BD: %s", subscription_id)
        return

    # Idempotencia: si ya fue procesado, ignorar
    if payment.status == "active":
        return

    payment.status = "active"
    db.session.flush()

    email     = payment.email
    nombre    = payment.nombre or email
    empresa   = payment.empresa or ""
    pais      = payment.pais or ""
    plan_name = payment.plan_name

    msg = (
        f"Nuevo cliente ha contratado el plan {plan_name}. "
        f"Email: {email}. Revisar y crear usuario."
    )
    _notify_staff(msg, "Nueva suscripción — acción requerida", payment.id)
    db.session.commit()

    try:
        send_email(
            to=email,
            subject="FinOps Latam — Bienvenido, tu pago fue confirmado",
            body=build_payment_welcome_email(nombre=nombre, plan_name=plan_name),
        )
    except Exception:
        logger.exception("Error enviando email de bienvenida a %s", email)

    try:
        for staff in _get_staff_users():
            if staff.email:
                send_email(
                    to=staff.email,
                    subject=f"FinOps Latam — Nuevo pago: {plan_name}",
                    body=build_admin_new_payment_email(
                        nombre=nombre,
                        empresa=empresa,
                        email=email,
                        pais=pais,
                        plan_name=plan_name,
                        subscription_id=subscription_id,
                    ),
                )
    except Exception:
        logger.exception("Error enviando emails de notificación a staff")


@webhooks_bp.route("/paypal", methods=["POST"])
def paypal_webhook():
    """
    POST /api/webhooks/paypal
    Recibe eventos de PayPal y los procesa.
    Valida la firma antes de procesar cualquier evento.
    """
    payload = request.get_data()
    headers = request.headers

    if not verify_webhook_signature(headers, payload):
        logger.warning("Webhook PayPal con firma inválida")
        return jsonify({"error": "Invalid signature"}), 400

    event      = request.get_json(silent=True) or {}
    event_type = event.get("event_type", "")
    resource   = event.get("resource", {})

    if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
        try:
            _handle_subscription_activated(resource)
        except Exception:
            logger.exception("Error procesando BILLING.SUBSCRIPTION.ACTIVATED")
            return jsonify({"error": "Error interno"}), 500

    return jsonify({"received": True}), 200
