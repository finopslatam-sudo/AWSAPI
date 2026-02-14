"""
ADMIN CLIENTS ROUTES
===================

Endpoints administrativos para gestión de clientes (empresas).

Este módulo:
- NO gestiona usuarios
- NO contiene lógica de negocio compleja
- DELEGA construcción de vistas al service layer
"""

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.admin_clients_service import (
    get_clients_with_active_plan
)
from src.models.client import Client
from src.models.plan import Plan
from src.models.subscription import ClientSubscription
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

    # 🔒 NUEVO: validar estado activo
    if not user.is_active:
        return None

    if user.global_role not in ("root", "admin", "support"):
        return None

    return user

# =====================================================
# ROUTES - LISTAR CLIENTES
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

# =====================================================
# ROUTES - CREAR CLIENTE (OWNER OBLIGATORIO)
# =====================================================
@admin_clients_bp.route("", methods=["POST"])
@jwt_required()
def create_client():

    actor = User.query.get(int(get_jwt_identity()))
    if not actor or actor.global_role not in ("root", "admin"):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json() or {}

    company_name = data.get("company_name")
    email = data.get("email")
    contact_name = data.get("contact_name")
    phone = data.get("phone")
    is_active = data.get("is_active", True)
    plan_id = data.get("plan_id")

    owner_data = data.get("owner")

    # =====================================================
    # VALIDACIONES CLIENTE
    # =====================================================
    if not company_name:
        return jsonify({"error": "company_name es obligatorio"}), 400

    if not email:
        return jsonify({"error": "email es obligatorio"}), 400

    if not plan_id:
        return jsonify({"error": "plan_id es obligatorio"}), 400

    if not owner_data:
        return jsonify({"error": "Owner obligatorio"}), 400

    plan = Plan.query.get(plan_id)
    if not plan:
        return jsonify({"error": "Plan no válido"}), 400

    if Client.query.filter_by(email=email.strip().lower()).first():
        return jsonify({"error": "Ya existe un cliente con ese email"}), 409
    
    if Client.query.filter_by(company_name=company_name.strip()).first():
        return jsonify({
            "error": "Ya existe un cliente con ese nombre"}), 409

    # =====================================================
    # VALIDACIONES OWNER
    # =====================================================
    owner_email = owner_data.get("email")
    owner_contact_name = owner_data.get("contact_name")
    password = owner_data.get("password")
    password_confirm = owner_data.get("password_confirm")

    if not owner_email or not owner_contact_name:
        return jsonify({"error": "Datos de owner incompletos"}), 400

    if not password or len(password) < 8:
        return jsonify({"error": "Password inválida"}), 400

    if password != password_confirm:
        return jsonify({"error": "Las contraseñas no coinciden"}), 400

    if User.query.filter_by(email=owner_email.strip().lower()).first():
        return jsonify({"error": "El usuario owner ya existe"}), 409

    # =====================================================
    # TRANSACCIÓN ATÓMICA
    # =====================================================
    try:

        # ----------------------
        # Crear cliente
        # ----------------------
        client = Client(
            company_name=company_name.strip(),
            email=email.strip().lower(),
            contact_name=contact_name.strip() if contact_name else None,
            phone=phone.strip() if phone else None,
            is_active=is_active,
        )

        db.session.add(client)
        db.session.flush()

        # ----------------------
        # Crear suscripción
        # ----------------------
        subscription = ClientSubscription(
            client_id=client.id,
            plan_id=plan.id,
            is_active=True,
        )

        db.session.add(subscription)

        # ----------------------
        # Crear usuario OWNER
        # ----------------------
        owner = User(
            email=owner_email.strip().lower(),
            contact_name=owner_contact_name.strip(),
            global_role=None,
            client_id=client.id,
            client_role="owner",
            is_active=True,
            force_password_change=True,
        )

        owner.set_password(password)

        db.session.add(owner)

        # ----------------------
        # COMMIT FINAL
        # ----------------------
        db.session.commit()

        # ----------------------
        # Evento email
        # ----------------------
        from src.services.user_events_service import (
            on_user_created_with_password
        )

        try:
            on_user_created_with_password(owner, password)
        except Exception:
            current_app.logger.exception(
                "[OWNER_WELCOME_EMAIL_FAILED] user_id=%s",
                owner.id,
            )

        return jsonify({
            "data": {
                "client_id": client.id,
                "company_name": client.company_name,
                "owner_id": owner.id,
                "owner_email": owner.email,
                "plan": plan.name,
            }
        }), 201

    except Exception:
        db.session.rollback()
        current_app.logger.exception("[CREATE_CLIENT_FAILED]")
        return jsonify({"error": "Error interno"}), 500


# =====================================================
# ROUTES - ACTUALIZAR CLIENTE (SIN PLAN)
# =====================================================
@admin_clients_bp.route("/<int:client_id>", methods=["PATCH"])
@jwt_required()
def update_client(client_id):
    """
    Actualiza datos del cliente.

    Permisos:
    - ROOT
    - ADMIN

    Nota:
    - NO actualiza plan
    - NO actualiza created_at
    """

    actor = User.query.get(int(get_jwt_identity()))
    if not actor or actor.global_role not in ("root", "admin"):
        return jsonify({"error": "Unauthorized"}), 403

    client = Client.query.get_or_404(client_id)
    data = request.get_json() or {}

    for field in (
        "company_name",
        "email",
        "contact_name",
        "phone",
        "is_active",
    ):
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

# =====================================================
# ROUTES - CAMBIAR PLAN CLIENTE
# =====================================================
@admin_clients_bp.route("/<int:client_id>/subscription", methods=["PATCH"])
@jwt_required()
def change_client_subscription(client_id):
    """
    Cambia el plan de un cliente (admin).

    Permisos:
    - ROOT
    - ADMIN

    Regla:
    - Nunca se edita una suscripción
    - Siempre se crea una nueva
    """

    actor = User.query.get(int(get_jwt_identity()))
    if not actor or actor.global_role not in ("root", "admin"):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json() or {}
    plan_id = data.get("plan_id")

    if not plan_id:
        return jsonify({"error": "plan_id es obligatorio"}), 400

    client = Client.query.get_or_404(client_id)
    plan = Plan.query.get(plan_id)

    if not plan:
        return jsonify({"error": "Plan no válido"}), 400

    # Desactivar suscripción activa actual
    ClientSubscription.query.filter_by(
        client_id=client.id,
        is_active=True
    ).update({"is_active": False})

    # Crear nueva suscripción
    subscription = ClientSubscription(
        client_id=client.id,
        plan_id=plan.id,
        is_active=True,
    )

    db.session.add(subscription)
    db.session.commit()

    return jsonify({
        "data": {
            "client_id": client.id,
            "plan": plan.name
        }
    }), 200
