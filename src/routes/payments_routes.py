"""
PAYMENTS ROUTES — STRIPE
========================
Endpoint público para iniciar el flujo de suscripción con Stripe.

NO requiere JWT — el usuario aún no tiene cuenta.
Flujo:
  1. Frontend envía datos del cliente
  2. Backend crea Customer + Subscription en Stripe (estado: incomplete)
  3. Backend retorna client_secret
  4. Frontend usa stripe.confirmPayment(client_secret) para procesar la tarjeta
  5. Stripe activa la suscripción y cobra mensualmente de forma automática
"""

import logging
from flask import Blueprint, jsonify, request

from src.models.database import db
from src.models.stripe_payment import Payment
from src.services.stripe_service import PLAN_NAMES, create_customer, create_subscription

logger = logging.getLogger("payments")

payments_bp = Blueprint("payments", __name__, url_prefix="/api/payments")


@payments_bp.route("/create-subscription", methods=["POST"])
def create_subscription_endpoint():
    """
    POST /api/payments/create-subscription

    Body: { plan_code, email, nombre, empresa, pais, telefono }
    Response 200: { client_secret, subscription_id }
    Response 400: { error }
    Response 502: { error }
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
        customer_id = create_customer(email, nombre, empresa)
        subscription_id, client_secret = create_subscription(
            customer_id,
            plan_code,
            metadata={"plan_code": plan_code, "empresa": empresa, "pais": pais},
        )

        payment = Payment(
            email=email,
            nombre=nombre,
            empresa=empresa,
            pais=pais,
            telefono=telefono,
            plan_code=plan_code,
            plan_name=plan_name,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            status="pending_payment",
        )
        db.session.add(payment)
        db.session.commit()

        return jsonify({
            "client_secret":   client_secret,
            "subscription_id": subscription_id,
        }), 200

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Error creando suscripción Stripe")
        return jsonify({"error": "Error al conectar con el proveedor de pago"}), 502
