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
        "clients": [
            {
                "id": c.id,
                "company_name": c.company_name,
                "email": c.email,
                "contact_name": c.contact_name,
                "phone": c.phone,
                "is_active": c.is_active,
                "created_at": c.created_at.isoformat(),
            }
            for c in clients
        ]
    }), 200


# =====================================================
# ADMIN — CREAR CLIENTE (SIN PASSWORD)
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

    # ----------------------------
    # VALIDACIONES
    # ----------------------------
    if not company_name or not email:
        return jsonify({
            "error": "company_name y email son obligatorios"
        }), 400

    if Client.query.filter_by(email=email).first():
        return jsonify({
            "error": "Ya existe un cliente con ese email"
        }), 409

    # ----------------------------
    # CREAR CLIENTE
    # ----------------------------
    client = Client(
        company_name=company_name,
        email=email,
        contact_name=contact_name,
        phone=phone,
        is_active=True,
        role="client",
        is_root=False,
    )

    db.session.add(client)
    db.session.commit()

    return jsonify({
        "id": client.id,
        "company_name": client.company_name,
        "email": client.email,
        "contact_name": client.contact_name,
        "phone": client.phone,
        "is_active": client.is_active,
        "created_at": client.created_at.isoformat(),
    }), 201


# =====================================================
# ADMIN — ACTIVAR / DESACTIVAR CLIENTE
# =====================================================
@admin_clients_bp.route("/clients/<int:client_id>", methods=["PUT"])
@jwt_required()
def update_client(client_id: int):
    actor = require_staff(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Acceso denegado"}), 403

    client = Client.query.get(client_id)
    if not client:
        return jsonify({"error": "Cliente no encontrado"}), 404

    data = request.get_json() or {}

    client.company_name = data.get("company_name", client.company_name)
    client.contact_name = data.get("contact_name", client.contact_name)
    client.phone = data.get("phone", client.phone)

    if "is_active" in data:
        client.is_active = bool(data["is_active"])

    db.session.commit()

    return jsonify({
        "message": "Cliente actualizado correctamente"
    }), 200
