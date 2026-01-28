"""
ADMIN CLIENTS ROUTES
===================

Endpoints administrativos para gestión de clientes (empresas).

Este módulo:
- NO gestiona usuarios
- NO contiene lógica de negocio compleja
- DELEGA construcción de vistas al service layer
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.admin_clients_service import (
    get_clients_with_active_plan
)
from src.models.client import Client
from src.models.database import db

# =====================================================
# BLUEPRINT
# =====================================================
admin_clients_bp = Blueprint(
    "admin_clients",
    __name__,
    url_prefix="/api/admin/clients"
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
    if user.global_role not in ("root", "admin", "support"):
        return None
    return user

# =====================================================
# ROUTES
# =====================================================

@admin_clients_bp.route("", methods=["GET"])
@jwt_required()
def list_clients():
    """
    Lista clientes para panel administrativo.

    Permisos:
    - ROOT
    - ADMIN
    - SUPPORT

    Contrato:
    {
        data: [...],
        meta: { total }
    }
    """

    actor = require_staff(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Unauthorized"}), 403

    clients = get_clients_with_active_plan()

    return jsonify({
        "data": clients,
        "meta": {
            "total": len(clients)
        }
    }), 200


@admin_clients_bp.route("", methods=["POST"])
@jwt_required()
def create_client():
    """
    Crea un nuevo cliente (empresa).

    Permisos:
    - ROOT
    - ADMIN
    """

    actor = User.query.get(int(get_jwt_identity()))
    if not actor or actor.global_role not in ("root", "admin"):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json() or {}

    company_name = data.get("company_name")
    email = data.get("email")
    contact_name = data.get("contact_name")
    phone = data.get("phone")
    is_active = data.get("is_active", True)

    if not company_name:
        return jsonify({"error": "company_name es obligatorio"}), 400

    if not email:
        return jsonify({"error": "email es obligatorio"}), 400

    from src.models.client import Client
    from src.models.database import db

    if Client.query.filter_by(email=email).first():
        return jsonify({"error": "Ya existe un cliente con ese email"}), 409

    client = Client(
        company_name=company_name,
        email=email,
        contact_name=contact_name,
        phone=phone,
        is_active=is_active,
    )

    db.session.add(client)
    db.session.commit()

    return jsonify({
        "data": {
            "id": client.id,
            "company_name": client.company_name,
            "email": client.email,
            "contact_name": client.contact_name,
            "phone": client.phone,
            "is_active": client.is_active,
            "created_at": (
                client.created_at.isoformat()
                if client.created_at else None
            ),
        }
    }), 201

@admin_clients_bp.route("/<int:client_id>", methods=["PATCH"])
@jwt_required()
def update_client(client_id):
    actor = User.query.get(int(get_jwt_identity()))
    if not actor or actor.global_role not in ("root", "admin"):
        return jsonify({"error": "Unauthorized"}), 403

    client = Client.query.get_or_404(client_id)
    data = request.get_json() or {}

    for field in ("company_name", "email", "contact_name", "phone", "is_active"):
        if field in data:
            setattr(client, field, data[field])

    db.session.commit()

    return jsonify({
        "data": {
            "id": client.id,
            "company_name": client.company_name,
            "email": client.email,
            "contact_name": client.contact_name,
            "phone": client.phone,
            "is_active": client.is_active,
        }
    }), 200

