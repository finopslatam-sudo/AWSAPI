from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import User
from src.models.database import db
from src.services.password_service import validate_password_policy

me_bp = Blueprint("me", __name__, url_prefix="/api/me")

# =====================================================
# USER - CAMBIA SU PASSWORD VOLUNTARIAMENTE
# =====================================================
@me_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_my_password():
    user = User.query.get(get_jwt_identity())
    data = request.get_json() or {}

    if not user.check_password(data.get("current_password")):
        return jsonify({"error": "Password actual incorrecta"}), 400

    new_password = data.get("new_password")
    if not new_password or len(new_password) < 8:
        return jsonify({"error": "Password inválida"}), 400

    user.set_password(new_password)
    user.force_password_change = False
    user.password_expires_at = None

    db.session.commit()

    # send_password_changed_email(user.email)

    return jsonify({"ok": True}), 200
