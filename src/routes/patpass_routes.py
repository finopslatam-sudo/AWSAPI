"""
PATPASS ROUTES
==============
Endpoints para integración con PatPass Comercio (Transbank).

Flujo:
  1. POST /api/patpass/create-inscription  → backend crea inscripción, retorna redirect_url
  2. Usuario autoriza en Transbank
  3. Transbank redirige a /pago/patpass-return?token_ws=XXX (frontend)
  4. Frontend llama POST /api/patpass/confirm con {token_ws}
  5. Backend confirma con Transbank y guarda tbk_user
"""

import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from src.models.database import db
from src.models.patpass_inscription import PatpassInscription
from src.services.patpass_service import (
    PLAN_NAMES,
    confirm_inscription,
    create_inscription,
    get_plan_amount,
)

logger = logging.getLogger("patpass")

patpass_bp = Blueprint("patpass", __name__, url_prefix="/api/patpass")

_BUY_ORDER_COUNTER = 0


def _generate_buy_order(plan_code: str) -> str:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"PP-{plan_code[:4].upper()}-{ts}"


@patpass_bp.route("/create-inscription", methods=["POST"])
def create_inscription_endpoint():
    """
    POST /api/patpass/create-inscription
    Body: { plan_code, email, nombre, empresa, pais, telefono }
    Response 200: { redirect_url, buy_order }
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
        return jsonify({"error": "Plan no disponible con este método de pago"}), 400

    buy_order  = _generate_buy_order(plan_code)
    amount_clp = get_plan_amount(plan_code)

    try:
        redirect_url, token = create_inscription(
            plan_code=plan_code,
            email=email,
            buy_order=buy_order,
        )

        inscription = PatpassInscription(
            email=email,
            nombre=nombre,
            empresa=empresa,
            pais=pais,
            telefono=telefono,
            plan_code=plan_code,
            plan_name=plan_name,
            buy_order=buy_order,
            amount_clp=amount_clp,
            status="pending",
        )
        db.session.add(inscription)
        db.session.commit()

        return jsonify({"redirect_url": redirect_url, "buy_order": buy_order}), 200

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Error creando inscripción PatPass")
        return jsonify({"error": "Error al conectar con Transbank"}), 502


@patpass_bp.route("/confirm", methods=["POST"])
def confirm_endpoint():
    """
    POST /api/patpass/confirm
    Body: { token_ws, buy_order }
    Response 200: { status, plan_code, plan_name }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Payload inválido"}), 400

    token_ws  = str(data.get("token_ws",  "")).strip()
    buy_order = str(data.get("buy_order", "")).strip()

    if not token_ws or not buy_order:
        return jsonify({"error": "token_ws y buy_order son requeridos"}), 400

    inscription = PatpassInscription.query.filter_by(buy_order=buy_order).first()
    if not inscription:
        return jsonify({"error": "Inscripción no encontrada"}), 404

    try:
        result = confirm_inscription(token_ws)

        if result.get("is_inscribed"):
            inscription.tbk_user           = result.get("tbk_user")
            inscription.authorization_code  = result.get("authorization_code")
            inscription.card_type           = result.get("card_type")
            inscription.card_last_four      = result.get("card_number")
            inscription.status              = "active"
            inscription.confirmed_at        = datetime.utcnow()
        else:
            inscription.status = "rejected"

        db.session.commit()

        return jsonify({
            "status":    inscription.status,
            "plan_code": inscription.plan_code,
            "plan_name": inscription.plan_name,
        }), 200

    except Exception:
        logger.exception("Error confirmando inscripción PatPass buy_order=%s", buy_order)
        inscription.status = "rejected"
        db.session.commit()
        return jsonify({"error": "Error al confirmar con Transbank"}), 502
