# =====================================================
# ADMIN USERS ROUTES
# =====================================================

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.database import db
from src.models.user import User
from src.models.client import Client
from src.services.password_service import (
    generate_temp_password,
    get_temp_password_expiration
)
from src.services.user_events_service import (
    on_user_deactivated,
    on_user_reactivated,
    on_admin_reset_password,
)

# =====================================================
# BLUEPRINT
# =====================================================
admin_users_bp = Blueprint(
    "admin_users",
    __name__,
    url_prefix="/api/admin"
)

# =====================================================
# HELPERS
# =====================================================

def require_staff(user_id: int) -> User | None:
    user = User.query.get(user_id)

    if not user:
        return None

    if not user.is_active:
        return None

    if user.global_role not in ("root", "admin", "support"):
        return None

    return user

# =====================================================
# NUEVA MATRIZ RESET PASSWORD
# =====================================================
def can_reset_password(actor: User, target: User) -> bool:
    """
    Matriz final de permisos:

    root → puede todo
    admin → puede todo excepto root
    support → puede:
        - resetear usuarios cliente
        - resetear su propia cuenta
    """

    if actor.global_role == "root":
        return True

    if actor.global_role == "admin":
        return target.global_role != "root"

    if actor.global_role == "support":
        if actor.id == target.id:
            return True
        if target.global_role is None:
            return True
        return False

    return False


# =====================================================
# NUEVA MATRIZ EDIT USER
# =====================================================
def can_edit_user(actor: User, target: User) -> bool:
    """
    Matriz final de permisos de edición.
    """

    if actor.global_role == "root":
        return True

    if actor.global_role == "admin":
        if target.global_role == "root":
            return False
        return True

    if actor.global_role == "support":
        if target.global_role is None:
            return True
        return False

    return False


# =====================================================
# BUILD VIEW (SIN CAMBIOS EN LÓGICA)
# =====================================================
def build_admin_user_view(row, actor: User) -> dict:
    """
    Construye la vista administrativa de un usuario
    lista para renderizar en frontend.
    """

    is_global = row.global_role is not None
    role = row.global_role if is_global else row.client_role

    # Crear objeto temporal mínimo para permisos
    class TempUser:
        def __init__(self, row):
            self.id = row.id
            self.global_role = row.global_role

    target = TempUser(row)
    can_edit = can_edit_user(actor, target)

    return {
        "id": row.id,
        "email": row.email,
        "type": "global" if is_global else "client",
        "role": role,
        "is_active": row.is_active,
        "force_password_change": row.force_password_change,
        "company_name": row.company_name,
        "contact_name": row.contact_name,
        "client": (
            {
                "id": row.client_id,
                "company_name": row.company_name,
            }
            if row.client_id else None
        ),
        "can_edit": can_edit,
    }
# =====================================================
# ADMIN — Editar USUARIOS
# =====================================================
@admin_users_bp.route("/users/<int:user_id>", methods=["PATCH"])
@jwt_required()
def update_user(user_id):
    actor = require_staff(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Unauthorized"}), 403

    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    # =====================================================
    # 🔒 BLOQUEOS GLOBALES (APLICA A TODOS)
    # =====================================================

    # ❌ Nadie puede desactivarse a sí mismo
    if actor.id == user.id:
        if "is_active" in data and data["is_active"] is False:
            return jsonify({
                "error": "No puedes desactivar tu propia cuenta"
            }), 403

        # ❌ Nadie puede cambiar su propio rol
        if "global_role" in data or "client_role" in data:
            return jsonify({
                "error": "No puedes modificar tu propio rol"
            }), 403

    # =====================================================
    # 🟥 ROOT
    # =====================================================
    if actor.global_role == "root":

        # ===== EMAIL =====
        if "email" in data:
            user.email = data["email"]

        # ===== CONTACT NAME =====
        if "contact_name" in data:
            user.contact_name = (data["contact_name"] or "").strip() or None


        # ===== ACTIVE =====
        if "is_active" in data:
            user.is_active = bool(data["is_active"])

        # ===== GLOBAL ROLE =====
        if user.global_role and "global_role" in data:
            user.global_role = data["global_role"]

        # ===== CLIENT ROLE =====
        if not user.global_role and "client_role" in data:
            user.client_role = data["client_role"]

        db.session.commit()
        return jsonify({"ok": True}), 200

    # =====================================================
    # 🟦 ADMIN
    # =====================================================
    if actor.global_role == "admin":

        # ❌ No puede editar root
        if user.global_role == "root":
            return jsonify({
                "error": "No permitido editar root"
            }), 403

        # ===== EMAIL =====
        if "email" in data:
            user.email = data["email"]

        # ===== CONTACT NAME =====
        if "contact_name" in data:
            user.contact_name = (data["contact_name"] or "").strip() or None
          

        # ===== ACTIVE =====
        if "is_active" in data:
            user.is_active = bool(data["is_active"])

        # ===== GLOBAL ROLE =====
        if user.global_role and "global_role" in data:

            new_role = data["global_role"]

            # ❌ No puede asignar root
            if new_role == "root":
                return jsonify({
                    "error": "No permitido asignar rol root"
                }), 403

            user.global_role = new_role

        # ===== CLIENT ROLE =====
        if not user.global_role and "client_role" in data:
            user.client_role = data["client_role"]

        db.session.commit()
        return jsonify({"ok": True}), 200

    # =====================================================
    # 🟩 SUPPORT
    # =====================================================
    if actor.global_role == "support":

        # ❌ No puede editar cuentas globales
        if user.global_role is not None:
            return jsonify({
                "error": "No permitido editar cuentas globales"
            }), 403

        # ===== EMAIL =====
        if "email" in data:
            user.email = data["email"]

        # ===== CONTACT NAME =====
        if "contact_name" in data:
            user.contact_name = (data["contact_name"] or "").strip() or None
            
        # ===== ACTIVE =====
        if "is_active" in data:
            user.is_active = bool(data["is_active"])

        # ===== CLIENT ROLE =====
        if "client_role" in data:

            new_role = data["client_role"]

            # ❌ Support no puede asignar owner
            if new_role == "owner":
                return jsonify({
                    "error": "No permitido asignar rol owner"
                }), 403

            user.client_role = new_role

        db.session.commit()
        return jsonify({"ok": True}), 200

    return jsonify({"error": "Rol no autorizado"}), 403

# =====================================================
# ADMIN — RESET PASSWORD MANUAL
# =====================================================
@admin_users_bp.route("/users/<int:user_id>/set-password", methods=["POST"])
@jwt_required()
def admin_set_password(user_id):
    actor = require_staff(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Unauthorized"}), 403

    user = User.query.get_or_404(user_id)

    if not can_reset_password(actor, user):
        return jsonify({"error": "No tienes permiso para esta acción"}), 403

    data = request.get_json() or {}

    password = data.get("password")
    if not password or len(password) < 8:
        return jsonify({"error": "Password inválida"}), 400

    user.set_password(password)
    user.force_password_change = True
    user.password_expires_at = get_temp_password_expiration()

    db.session.commit()

    current_app.logger.info("[DEBUG] Ejecutando on_admin_reset_password para user_id=%s", user.id)

    try:
        on_admin_reset_password(user, password)
    except Exception:
        current_app.logger.exception(
            "[ADMIN_SET_PASSWORD_EMAIL_FAILED] user_id=%s",
            user.id,
        )

    return jsonify({"ok": True}), 200

# =====================================================
# USER - RECUPERA SU PASSWORD AL INICIAR SESION
# =====================================================
@admin_users_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@jwt_required()
def reset_user_password(user_id):
    actor = require_staff(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Unauthorized"}), 403

    user = User.query.get_or_404(user_id)

    if not can_reset_password(actor, user):
        return jsonify({"error": "No tienes permiso para esta acción"}), 403

    temp_password = generate_temp_password()

    user.set_password(temp_password)
    user.force_password_change = True
    user.password_expires_at = get_temp_password_expiration()

    db.session.commit()

    try:
        on_admin_reset_password(user, temp_password)
    except Exception:
        current_app.logger.exception(
            "[ADMIN_RESET_PASSWORD_EMAIL_FAILED] user_id=%s",
            user.id,
        )

    return jsonify({"ok": True}), 200

# =====================================================
# ADMIN — LISTAR USUARIOS
# =====================================================
@admin_users_bp.route("/users", methods=["GET"])
@jwt_required()
def list_users():
    actor = require_staff(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Acceso denegado"}), 403

    grouped = request.args.get("grouped") == "1"

    # =====================================================
    # MODO 1 — LISTADO PLANO (ACTUAL, NO SE ROMPE)
    # =====================================================
    if not grouped:
        rows = (
            db.session.query(
                User.id,
                User.email,
                User.global_role,
                User.client_role,
                User.client_id,
                User.is_active,
                User.force_password_change,
                User.contact_name,
                Client.company_name,
            )
            .outerjoin(Client, User.client_id == Client.id)
            .order_by(User.id.asc())
            .all()
        )

        data = [build_admin_user_view(r, actor) for r in rows]

        return jsonify({
            "data": data,
            "meta": {
                "total_users": len(data)
            }
        }), 200

    # =====================================================
    # MODO 2 — AGRUPADO POR CLIENTE (ENTERPRISE)
    # =====================================================
    clients = Client.query.order_by(Client.id.asc()).all()

    result = []
    total_users = 0

    for client in clients:
        users = (
            db.session.query(User)
            .filter(User.client_id == client.id)
            .order_by(User.id.asc())
            .all()
        )

        users_data = [
            build_admin_user_view(
                type("Row", (), {
                    "id": u.id,
                    "email": u.email,
                    "global_role": u.global_role,
                    "client_role": u.client_role,
                    "client_id": u.client_id,
                    "is_active": u.is_active,
                    "force_password_change": u.force_password_change,
                    "contact_name": u.contact_name,
                    "company_name": client.company_name,
                })(),
                actor
            )
            for u in users
        ]

        total_users += len(users_data)

        result.append({
            "client_id": client.id,
            "company_name": client.company_name,
            "plan": getattr(client, "plan_name", None),
            "users": users_data
        })

    return jsonify({
        "data": result,
        "meta": {
            "total_clients": len(result),
            "total_users": total_users
        }
    }), 200

# =====================================================
# ADMIN — CREAR USUARIO (CLIENTE)
# =====================================================
@admin_users_bp.route("", methods=["POST"])
@jwt_required()
def create_user():
    contact_name = (data.get("contact_name") or "").strip()

    actor = User.query.get(int(get_jwt_identity()))
    if not actor or not actor.is_active:
        return jsonify({"error": "Unauthorized"}), 403

    if actor.global_role not in ("root", "admin"):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json() or {}

    email = data.get("email")
    client_id = data.get("client_id")
    client_role = data.get("client_role")

    if not email:
        return jsonify({"error": "email es obligatorio"}), 400

    if not client_id:
        return jsonify({"error": "client_id es obligatorio"}), 400

    if client_role not in ("owner", "finops_admin", "viewer"):
        return jsonify({"error": "client_role inválido"}), 400


    if User.query.filter_by(email=email).first():
        return jsonify({"error": "El usuario ya existe"}), 409

    client = Client.query.get(client_id)
    if not client:
        return jsonify({"error": "Cliente no existe"}), 404

    temp_password = generate_temp_password()

    user = User(
        email=email.strip().lower(),
        contact_name=contact_name or None,
        global_role=None,
        client_id=client_id,
        client_role=client_role,
        is_active=True,
        force_password_change=True,
    )

    user.set_password(temp_password)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "data": {
            "id": user.id,
            "email": user.email,
            "role": user.client_role,
            "type": "client",
            "company_name": client.company_name,
            "is_active": user.is_active,
        }
    }), 201

# =====================================================
# ADMIN — CREAR USUARIO (GLOBAL O CLIENTE)
# =====================================================
@admin_users_bp.route("/users/with-password", methods=["POST"])
@jwt_required()
def create_user_with_password():
    actor = User.query.get(int(get_jwt_identity()))
    if not actor or not actor.is_active:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json() or {}

    user_type = data.get("type")  # "global" | "client"
    email = (data.get("email") or "").strip().lower()
    contact_name = (data.get("contact_name") or "").strip()
    password = data.get("password")
    password_confirm = data.get("password_confirm")
    force_change = bool(data.get("force_password_change", True))

    # =====================================================
    # VALIDACIONES BASE
    # =====================================================
    if user_type not in ("global", "client"):
        return jsonify({"error": "type inválido"}), 400

    if not email or not contact_name:
        return jsonify({
            "error": "Email y contact_name son obligatorios"
        }), 400

    if not password or len(password) < 8:
        return jsonify({"error": "Password inválida"}), 400

    if password != password_confirm:
        return jsonify({
            "error": "Las contraseñas no coinciden"
        }), 400

    if User.query.filter_by(email=email).first():
        return jsonify({
            "error": "El usuario ya existe"
        }), 409

    # =====================================================
    # CASO 1 — USUARIO GLOBAL
    # =====================================================
    if user_type == "global":

        global_role = data.get("global_role")

        if not global_role:
            return jsonify({
                "error": "global_role es obligatorio"
            }), 400

        # 🔴 ROOT puede crear cualquiera
        if actor.global_role == "root":
            if global_role not in ("root", "admin", "support"):
                return jsonify({
                    "error": "global_role inválido"
                }), 400

        # 🔵 ADMIN puede crear admin y support
        elif actor.global_role == "admin":
            if global_role not in ("admin", "support"):
                return jsonify({
                    "error": "Admin solo puede crear admin o support"
                }), 403

        # 🟢 SUPPORT no puede crear globales
        else:
            return jsonify({
                "error": "No tienes permiso para crear usuarios globales"
            }), 403

        user = User(
            email=email,
            contact_name=contact_name,
            global_role=global_role,
            client_id=None,
            client_role=None,
            is_active=True,
            force_password_change=force_change,
        )

    # =====================================================
    # CASO 2 — USUARIO CLIENTE
    # =====================================================
    else:

        # Solo staff puede crear cliente
        if actor.global_role not in ("root", "admin", "support"):
            return jsonify({
                "error": "No tienes permiso para crear usuarios cliente"
            }), 403

        client_id = data.get("client_id")
        client_role = data.get("client_role")

        if not client_id or not client_role:
            return jsonify({
                "error": "Datos incompletos"
            }), 400

        if client_role not in ("owner", "finops_admin", "viewer"):
            return jsonify({
                "error": "client_role inválido"
            }), 400

        client = Client.query.get(client_id)
        if not client:
            return jsonify({
                "error": "Cliente no existe"
            }), 404

        user = User(
            email=email,
            contact_name=contact_name,
            global_role=None,
            client_id=client_id,
            client_role=client_role,
            is_active=True,
            force_password_change=force_change,
        )

    # =====================================================
    # PERSISTENCIA SEGURA
    # =====================================================
    try:
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Error al crear usuario"
        }), 500

    # =====================================================
    # EVENTO EMAIL (NO BLOQUEANTE)
    # =====================================================
    from src.services.user_events_service import (
        on_user_created_with_password
    )

    try:
        on_user_created_with_password(user, password)
    except Exception:
        current_app.logger.exception(
            "[USER_WELCOME_EMAIL_FAILED] user_id=%s",
            user.id,
        )

    return jsonify({
        "data": {
            "id": user.id,
            "email": user.email,
            "type": user_type,
            "global_role": user.global_role,
            "client_id": user.client_id,
            "client_role": user.client_role,
            "is_active": user.is_active,
            "force_password_change": user.force_password_change,
        }
    }), 201



