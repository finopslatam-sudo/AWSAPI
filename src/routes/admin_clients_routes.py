# =====================================================
# ADMIN CLIENTS ROUTES
# =====================================================

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.database import db
from src.models.client import Client
from src.models.user import User

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
    if user.global_role not in ("root", "support"):
        return None
    return user


# =====================================================
# ADMIN — LISTAR CLIENTES
# =====================================================
@admin_clients_bp.route("/clients", methods=["GET"])
@jwt_required()
def list_clients():
    actor = require_staff(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Acceso denegado"}), 403

    clients = Client.query.order_by(Client.created_at.desc()).all()

    return jsonify({
        "clients": [c.to_dict() for c in clients]
    }), 200


# =====================================================
# ADMIN — CREAR CLIENTE
# =====================================================
@admin_clients_bp.route("/clients", methods=["POST"])
@jwt_required()
def create_client():
    actor = require_staff(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Acceso denegado"}), 403

    data = request.get_json() or {}

    company_name = data.get("company_name")
    email = data.get("email")
    contact_name = data.get("contact_name")
    phone = data.get("phone")

    if not company_name or not email:
        return jsonify({
            "error": "company_name y email son obligatorios"
        }), 400

    if Client.query.filter_by(email=email).first():
        return jsonify({
            "error": "Ya existe un cliente con ese email"
        }), 409

    client = Client(
        company_name=company_name,
        email=email,
        contact_name=contact_name,
        phone=phone,
        is_active=True
    )

    db.session.add(client)
    db.session.commit()

    return jsonify(client.to_dict()), 201
