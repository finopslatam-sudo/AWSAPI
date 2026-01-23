from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.admin_clients_service import get_clients_with_active_plan

# =====================================================
# BLUEPRINT
# =====================================================
admin_clients_bp = Blueprint(
    "admin_clients",
    __name__,
    url_prefix="/api/admin"
)


def register_admin_clients_routes(app):
    app.register_blueprint(admin_clients_bp)


# =====================================================
# HELPERS
# =====================================================
def require_staff(user_id: int) -> User | None:
    user = User.query.get(user_id)
    if not user:
        return None
    if user.global_role not in ("root", "admin"):
        return None
    return user


# =====================================================
# ADMIN — LISTAR CLIENTES (CON PLAN ACTIVO)
# =====================================================
@admin_clients_bp.route("/clients", methods=["GET"])
@jwt_required()
def list_clients():
    actor = require_staff(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Acceso denegado"}), 403

    clients = get_clients_with_active_plan()

    return jsonify({"clients": clients}), 200
