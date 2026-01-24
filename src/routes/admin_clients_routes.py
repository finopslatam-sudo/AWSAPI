"""
ADMIN CLIENTS ROUTES
===================

Endpoints administrativos para gestión de clientes (empresas).
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.database import db
from src.models.user import User
from src.models.client import Client

admin_clients_bp = Blueprint(
    "admin_clients",
    __name__,
    url_prefix="/api/admin/clients"
)


@admin_clients_bp.route("", methods=["POST"])
@jwt_required()
def create_client():
    """
    Crea un nuevo cliente (empresa).

    Permisos:
    - Solo ROOT / ADMIN

    Body esperado:
    {
        "company_name": "Empresa ABC",
        "email": "contacto@empresa.cl",
        "contact_name": "Juan Pérez",
        "phone": "+56 9 1234 5678",
        "is_active": true
    }
    """

    # ==========================
    # AUTH
    # ==========================
    user = User.query.get(int(get_jwt_identity()))

    if not user or user.global_role not in ("root", "admin"):
        return jsonify({"error": "Unauthorized"}), 403

    # ==========================
    # PAYLOAD
    # ==========================
    data = request.get_json() or {}

    company_name = data.get("company_name")
    email = data.get("email")
    contact_name = data.get("contact_name")
    phone = data.get("phone")
    is_active = data.get("is_active", True)

    # ==========================
    # VALIDATION
    # ==========================
    if not company_name:
        return jsonify({"error": "company_name es obligatorio"}), 400

    if not email:
        return jsonify({"error": "email es obligatorio"}), 400

    existing = Client.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "Ya existe un cliente con ese email"}), 409

    # ==========================
    # CREATE CLIENT
    # ==========================
    client = Client(
        company_name=company_name,
        email=email,
        contact_name=contact_name,
        phone=phone,
        is_active=is_active
    )

    db.session.add(client)
    db.session.commit()

    # ==========================
    # RESPONSE
    # ==========================
    return jsonify({
        "id": client.id,
        "company_name": client.company_name,
        "email": client.email,
        "contact_name": client.contact_name,
        "phone": client.phone,
        "is_active": client.is_active,
        "created_at": client.created_at.isoformat() if client.created_at else None
    }), 201
