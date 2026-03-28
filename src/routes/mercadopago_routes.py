"""
MERCADO PAGO ROUTES
===================
Endpoints para suscripciones y webhook de Mercado Pago.

ENDPOINTS PÚBLICOS (sin JWT — el cliente aún no tiene cuenta):
  POST /api/payments/mercadopago/subscription  — inicia suscripción, retorna init_point
  POST /api/webhooks/mercadopago               — recibe notificaciones de MP

FLUJO COMPLETO:
  1. Cliente llena formulario → POST /api/payments/mercadopago/subscription
  2. Backend crea preapproval en MP → retorna {init_point}
  3. Frontend redirige a init_point (página de pago de MP)
  4. Cliente paga → MP llama a POST /api/webhooks/mercadopago
  5. Backend valida estado real con la API de MP (NUNCA confiar en el webhook)
  6. Si status == 'authorized' → guardar como 'active' y notificar staff
  7. Admin activa la cuenta del cliente manualmente

SEGURIDAD:
  - Webhook sin JWT (lo llama el servidor de MP)
  - Idempotencia: si el registro ya está 'active', se ignora
  - Estado solo se actualiza tras verificación con la API oficial de MP
"""

import logging
from flask import Blueprint, jsonify, request

from src.models.database import db
from src.models.mp_subscription import MPSubscription
from src.models.user import User
from src.models.notification import Notification
from src.services.mercadopago_service import (
    PLAN_NAMES,
    create_subscription,
    get_subscription_status,
)
from src.services.email_service import send_email
from src.services.email_templates import (
    build_payment_welcome_email,
    build_admin_new_payment_email,
)

logger = logging.getLogger("mercadopago")

mercadopago_bp = Blueprint("mercadopago", __name__)

_STAFF_ROLES = ("root", "admin", "support")

# ─────────────────────────────────────────────
#  Helpers internos
# ─────────────────────────────────────────────

def _get_staff_users() -> list[User]:
    return User.query.filter(
        User.global_role.in_(_STAFF_ROLES),
        User.is_active == True,
    ).all()


def _notify_staff_in_app(message: str, title: str, ref_id: int) -> None:
    for staff in _get_staff_users():
        db.session.add(Notification(
            user_id=staff.id,
            type="new_subscription",
            title=title,
            message=message,
            reference_id=ref_id,
        ))


def _send_staff_emails(
    nombre: str, empresa: str, email: str,
    pais: str, plan_name: str, subscription_id: str,
) -> None:
    try:
        for staff in _get_staff_users():
            if staff.email:
                send_email(
                    to=staff.email,
                    subject=f"FinOps Latam — Nuevo pago MP: {plan_name}",
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
        logger.exception("Error enviando emails de notificación a staff (MP)")


def _activate_subscription(subscription: MPSubscription) -> None:
    """
    Marca la suscripción como 'active', notifica staff y envía email de bienvenida.
    Debe llamarse SOLO tras validar el estado con la API de MP.
    """
    subscription.status = "active"
    db.session.flush()

    nombre    = subscription.nombre or subscription.email
    empresa   = subscription.empresa or ""
    pais      = subscription.pais or ""
    plan_name = subscription.plan_name
    email     = subscription.email

    msg = (
        f"Nuevo cliente vía Mercado Pago — plan {plan_name}. "
        f"Email: {email}. Revisar y crear usuario."
    )
    _notify_staff_in_app(msg, "Nueva suscripción MP — acción requerida", subscription.id)
    db.session.commit()

    try:
        send_email(
            to=email,
            subject="FinOps Latam — Bienvenido, tu pago fue confirmado",
            body=build_payment_welcome_email(nombre=nombre, plan_name=plan_name),
        )
    except Exception:
        logger.exception("Error enviando email de bienvenida a %s", email)

    _send_staff_emails(nombre, empresa, email, pais, plan_name, subscription.mp_subscription_id or "")


# ─────────────────────────────────────────────
#  POST /api/payments/mercadopago/subscription
# ─────────────────────────────────────────────

@mercadopago_bp.route("/api/payments/mercadopago/subscription", methods=["POST"])
def create_mp_subscription():
    """
    Inicia una suscripción mensual con Mercado Pago.

    Body: { plan_code, email, nombre, empresa, pais, telefono }
    Response 200: { init_point, subscription_id }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Payload inválido"}), 400

    plan_code = str(data.get("plan_code", "")).strip().lower()
    email     = str(data.get("email",     "")).strip()[:320]
    nombre    = str(data.get("nombre",    "")).strip()[:255]
    empresa   = str(data.get("empresa",   "")).strip()[:255]
    pais      = str(data.get("pais",      "")).strip()[:100]
    telefono  = str(data.get("telefono",  "")).strip()[:50]

    if not plan_code or not email or "@" not in email:
        return jsonify({"error": "plan_code y email válidos son requeridos"}), 400
    if not nombre:
        return jsonify({"error": "El nombre es requerido"}), 400
    if not empresa:
        return jsonify({"error": "La empresa es requerida"}), 400

    plan_name = PLAN_NAMES.get(plan_code)
    if not plan_name:
        return jsonify({"error": "Plan inválido"}), 400

    try:
        preapproval_id, init_point = create_subscription(
            plan_code=plan_code,
            user_email=email,
            nombre=nombre,
            empresa=empresa,
            pais=pais,
        )

        subscription = MPSubscription(
            email=email,
            nombre=nombre,
            empresa=empresa,
            pais=pais,
            telefono=telefono,
            plan_code=plan_code,
            plan_name=plan_name,
            mp_subscription_id=preapproval_id,
            status="pending",
        )
        db.session.add(subscription)
        db.session.commit()

        return jsonify({
            "init_point":      init_point,
            "subscription_id": preapproval_id,
        }), 200

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Error creando suscripción Mercado Pago")
        return jsonify({"error": "Error al conectar con el proveedor de pago"}), 502


# ─────────────────────────────────────────────
#  POST /api/webhooks/mercadopago
# ─────────────────────────────────────────────

@mercadopago_bp.route("/api/webhooks/mercadopago", methods=["POST"])
def mercadopago_webhook():
    """
    Recibe notificaciones de Mercado Pago.

    REGLA CRÍTICA: NUNCA activar basándose en el cuerpo del webhook.
    Siempre consultar la API oficial de MP para verificar el estado real.

    MP envía: { type, data: { id } }
    """
    event = request.get_json(silent=True) or {}

    event_type      = event.get("type", "")
    resource_data   = event.get("data", {})
    preapproval_id  = str(resource_data.get("id", "")).strip()

    # Solo procesar eventos de suscripción
    if event_type != "subscription_preapproval":
        return jsonify({"received": True}), 200

    if not preapproval_id:
        logger.warning("Webhook MP sin preapproval_id en data.id")
        return jsonify({"received": True}), 200

    subscription = MPSubscription.query.filter_by(
        mp_subscription_id=preapproval_id,
    ).first()

    if not subscription:
        logger.warning("Suscripción MP no encontrada en BD: %s", preapproval_id)
        return jsonify({"received": True}), 200

    # Idempotencia: si ya fue activada, ignorar
    if subscription.status == "active":
        return jsonify({"received": True}), 200

    # ── VALIDACIÓN OBLIGATORIA CON LA API OFICIAL DE MP ──
    try:
        real_status = get_subscription_status(preapproval_id)
    except Exception:
        logger.exception("Error consultando estado de suscripción MP: %s", preapproval_id)
        return jsonify({"error": "Error interno"}), 500

    if real_status == "authorized":
        try:
            _activate_subscription(subscription)
        except Exception:
            logger.exception("Error activando suscripción MP: %s", preapproval_id)
            return jsonify({"error": "Error interno"}), 500
    elif real_status in ("paused", "cancelled"):
        subscription.status = real_status
        db.session.commit()

    return jsonify({"received": True}), 200
