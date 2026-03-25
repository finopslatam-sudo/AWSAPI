"""
assistant_routes.py
Endpoint de Finops.ia — chatbot AWS FinOps Enterprise.
"""
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import User
from src.services.assistant_service import chat

assistant_bp = Blueprint("assistant", __name__)


def _require_client_user(user_id: int):
    """Retorna el usuario cliente o None si es staff / no existe."""
    user = User.query.get(user_id)
    if not user or not user.is_active:
        return None
    if user.global_role is not None:
        return None  # staff no usa este endpoint
    return user


@assistant_bp.route("/api/client/assistant/chat", methods=["POST"])
@jwt_required()
def assistant_chat():
    user_id = get_jwt_identity()
    user = _require_client_user(user_id)
    if not user:
        return jsonify({"error": "Acceso denegado"}), 403

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Payload inválido"}), 400

    messages = data.get("messages", [])
    is_new = bool(data.get("is_new_conversation", False))

    if not isinstance(messages, list):
        return jsonify({"error": "messages debe ser una lista"}), 400

    # Limitar historial a últimos 20 mensajes (10 turnos) para control de costos
    messages = messages[-20:]

    try:
        response_text = chat(messages, is_new)
        return jsonify({"response": response_text}), 200
    except RuntimeError as e:
        current_app.logger.error(f"[Finops.ia] Config error: {e}")
        return jsonify({"error": "Servicio no disponible temporalmente"}), 503
    except Exception as e:
        current_app.logger.error(f"[Finops.ia] Error: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500
