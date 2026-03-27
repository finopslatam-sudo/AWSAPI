"""
PAYMENTS ROUTES
===============
Endpoint público para iniciar el flujo de pago con PayPal.

NO requiere JWT — el usuario aún no tiene cuenta.
La seguridad del pago la gestiona PayPal directamente.
"""

from flask import Blueprint, jsonify, request, current_app
import requests as http_requests

from src.models.database import db
from src.models.stripe_payment import Payment
from src.services.paypal_service import create_subscription, PLAN_NAMES

payments_bp = Blueprint("payments", __name__, url_prefix="/api/payments")


@payments_bp.route("/create-checkout-session", methods=["POST"])
def create_checkout():
    """
    POST /api/payments/create-checkout-session

    Body JSON:
      plan_code : str  — foundation | professional | enterprise | consultoria
      email     : str  — email del comprador
      nombre    : str  — nombre completo
      empresa   : str  — nombre de la empresa
      pais      : str  — país
      telefono  : str  — teléfono (opcional)

    Response:
      200: { checkout_url: "https://www.paypal.com/..." }
      400: { error: "..." }
      502: { error: "Error al conectar con el proveedor de pago" }
      500: { error: "Error interno del servidor" }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Payload inválido"}), 400

    plan_code = str(data.get("plan_code", "")).strip()
    email     = str(data.get("email", "")).strip()[:320]
    nombre    = str(data.get("nombre", "")).strip()[:255]
    empresa   = str(data.get("empresa", "")).strip()[:255]
    pais      = str(data.get("pais", "")).strip()[:100]
    telefono  = str(data.get("telefono", "")).strip()[:50]

    if plan_code not in PLAN_NAMES:
        return jsonify({"error": "Plan no válido"}), 400
    if not email or "@" not in email:
        return jsonify({"error": "Email inválido"}), 400
    if not nombre:
        return jsonify({"error": "El nombre es requerido"}), 400
    if not empresa:
        return jsonify({"error": "La empresa es requerida"}), 400

    try:
        subscription_id, approval_url = create_subscription(
            plan_code=plan_code,
            email=email,
            nombre=nombre,
            empresa=empresa,
            pais=pais,
            telefono=telefono,
        )

        # Guardar pre-pago en BD — el webhook buscará por subscription_id
        payment = Payment(
            email=email,
            nombre=nombre,
            empresa=empresa,
            pais=pais,
            telefono=telefono,
            plan_code=plan_code,
            plan_name=PLAN_NAMES[plan_code],
            paypal_subscription_id=subscription_id,
            status="pending_approval",
        )
        db.session.add(payment)
        db.session.commit()

        return jsonify({"checkout_url": approval_url}), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except http_requests.HTTPError:
        return jsonify({"error": "Error al conectar con el proveedor de pago"}), 502
    except Exception:
        current_app.logger.exception("Error creando suscripción PayPal")
        return jsonify({"error": "Error interno del servidor"}), 500
