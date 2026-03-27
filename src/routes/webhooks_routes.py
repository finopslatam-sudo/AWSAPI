"""
WEBHOOKS ROUTES — PAYPAL
========================
Recibe eventos de PayPal Subscriptions y ejecuta la lógica post-pago.

Flujo para BILLING.SUBSCRIPTION.ACTIVATED:
  1. Verificar firma del webhook (PAYPAL_WEBHOOK_ID)
  2. Buscar Payment por paypal_subscription_id y actualizar status
  3. Enviar email de bienvenida al cliente
  4. Enviar email de notificación a todos los staff (root/admin/support)
  5. Crear notificación in-app para cada usuario staff

SEGURIDAD:
  - Sin JWT (PayPal llama directamente)
  - Firma verificada con la API de PayPal
  - Idempotencia: status 'pending_activation' previene reprocesamiento
"""

import json
import logging
from flask import Blueprint, jsonify, request

from src.models.database import db
from src.models.stripe_payment import Payment
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
    """Procesa el evento BILLING.SUBSCRIPTION.ACTIVATED."""
    subscription_id = resource.get("id", "")

    # Buscar el payment pre-guardado cuando se inició el checkout
    payment = Payment.query.filter_by(paypal_subscription_id=subscription_id).first()
    if not payment:
        logger.warning("Suscripción PayPal no encontrada en BD: %s", subscription_id)
        return

    # Idempotencia: si ya fue procesado, ignorar
    if payment.status == "pending_activation":
        logger.info("Webhook duplicado ignorado: subscription_id=%s", subscription_id)
        return

    payment.status = "pending_activation"
    db.session.flush()

    email     = payment.email
    nombre    = payment.nombre or email
    empresa   = payment.empresa or ""
    pais      = payment.pais or ""
    plan_name = payment.plan_name

    # Notificaciones in-app para staff
    msg = (
        f"Nuevo cliente ha contratado el plan {plan_name}. "
        f"Email: {email}. Revisar y crear usuario."
    )
    _notify_staff(msg, "Nueva suscripción — acción requerida", payment.id)
    db.session.commit()

    # Email al cliente
    try:
        send_email(
            to=email,
            subject="FinOps Latam — Bienvenido, tu pago fue confirmado",
            body=build_payment_welcome_email(nombre=nombre, plan_name=plan_name),
        )
    except Exception:
        logger.exception("Error enviando email de bienvenida a %s", email)

    # Email a staff
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
                        paypal_subscription_id=subscription_id,
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
    body    = request.get_data()
    headers = request.headers

    if not verify_webhook_signature(headers, body):
        logger.warning("Firma de webhook PayPal inválida")
        return jsonify({"error": "Invalid signature"}), 400

    try:
        event = json.loads(body)
    except Exception:
        return jsonify({"error": "Bad payload"}), 400

    event_type = event.get("event_type", "")

    if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
        try:
            _handle_subscription_activated(event.get("resource", {}))
        except Exception:
            logger.exception("Error procesando BILLING.SUBSCRIPTION.ACTIVATED")
            return jsonify({"error": "Error interno del servidor"}), 500

    return jsonify({"received": True}), 200
