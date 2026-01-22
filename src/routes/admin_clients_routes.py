# =====================================================
# ADMIN CLIENTS ROUTES
# =====================================================

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
import secrets
import string

from src.models.database import db
from src.models.client import Client
from src.models.user import User
from src.services.user_events_service import on_forgot_password
from src.services.password_service import generate_temp_password


admin_clients_bp = Blueprint(
    "admin_clients",
    __name__,
    url_prefix="/api/admin"
)


def register_admin_clients_routes(app):
    app.register_blueprint(admin_clients_bp)


def generate_temp_password(length=10):
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


# =====================================================
# ADMIN — CREAR CLIENTE
# =====================================================
@admin_clients_bp.route("/clients", methods=["POST"])
@jwt_required()
def create_client():
    actor = User.query.get(int(get_jwt_identity()))

    # 🔐 permisos
    if not actor or actor.global_role not in ("root", "support"):
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

    # ❌ evitar duplicados
    if Client.query.filter_by(email=email).first():
        return jsonify({
            "error": "Ya existe un cliente con ese email"
        }), 409

    temp_password = generate_temp_password()

    client = Client(
        company_name=company_name,
        email=email,
        contact_name=contact_name,
        phone=phone,
        is_active=True,
        role="client",
        force_password_change=True
    )

    client.set_password(temp_password)

    db.session.add(client)
    db.session.commit()

    # 📧 evento (reutilizamos forgot password)
    on_forgot_password(client, temp_password)

    return jsonify({
        "id": client.id,
        "company_name": client.company_name,
        "email": client.email,
        "is_active": client.is_active,
        "created_at": client.created_at.isoformat()
    }), 201
