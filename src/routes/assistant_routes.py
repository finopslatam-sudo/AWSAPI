"""
assistant_routes.py
Endpoint de Finops.ia — motor de respuestas local, sin API externa.
"""
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import User
from src.services.assistant_response_engine import get_response

assistant_bp = Blueprint("assistant", __name__)


def _require_client_user(user_id: int):
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
    aws_account_id = data.get("aws_account_id")

    if not isinstance(messages, list):
        return jsonify({"error": "messages debe ser una lista"}), 400

    if aws_account_id is not None:
        try:
            aws_account_id = int(aws_account_id)
        except (TypeError, ValueError):
            return jsonify({"error": "aws_account_id inválido"}), 400

    # Obtener el último mensaje del usuario
    last_message = ""
    for m in reversed(messages):
        if m.get("role") == "user" and m.get("content"):
            last_message = str(m["content"])
            break

    try:
        response_text = get_response(last_message, user.client_id, aws_account_id, is_new)
        return jsonify({"response": response_text}), 200
    except Exception as e:
        current_app.logger.error(f"[Finops.ia] Error: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500
