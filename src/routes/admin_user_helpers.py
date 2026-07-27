# =====================================================
# ADMIN USERS — SHARED HELPERS
# =====================================================
# Shared permission helpers and view builder used by
# admin_users_routes.py and admin_user_access_routes.py

from flask import jsonify

from src.models.user import User
from src.models.client import Client


# =====================================================
# REQUIRE STAFF
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
# VALIDAR + CONSTRUIR USUARIO (GLOBAL O CLIENTE)
# =====================================================
def validate_new_user_payload(actor: User, user_type: str, email: str, contact_name: str,
                               password: str, password_confirm: str):
    """
    Validaciones base compartidas por ambos tipos de alta (global/cliente).
    Devuelve una respuesta de error (jsonify, status) o None si todo es válido.
    """
    if user_type not in ("global", "client"):
        return jsonify({"error": "type inválido"}), 400

    if not email or not contact_name:
        return jsonify({"error": "Email y contact_name son obligatorios"}), 400

    if not password or len(password) < 8:
        return jsonify({"error": "Password inválida"}), 400

    if password != password_confirm:
        return jsonify({"error": "Las contraseñas no coinciden"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "El usuario ya existe"}), 409

    return None


def build_global_user(actor: User, data: dict, email: str, contact_name: str, force_change: bool):
    """Construye (sin persistir) un usuario global, validando la matriz de permisos."""
    global_role = data.get("global_role")

    if not global_role:
        return None, (jsonify({"error": "global_role es obligatorio"}), 400)

    if actor.global_role == "root":
        if global_role not in ("root", "admin", "support"):
            return None, (jsonify({"error": "global_role inválido"}), 400)
    elif actor.global_role == "admin":
        if global_role not in ("admin", "support"):
            return None, (jsonify({"error": "Admin solo puede crear admin o support"}), 403)
    else:
        return None, (jsonify({"error": "No tienes permiso para crear usuarios globales"}), 403)

    user = User(
        email=email,
        contact_name=contact_name,
        global_role=global_role,
        client_id=None,
        client_role=None,
        is_active=True,
        force_password_change=force_change,
    )
    return user, None


def build_client_user(actor: User, data: dict, email: str, contact_name: str, force_change: bool):
    """Construye (sin persistir) un usuario cliente, validando la matriz de permisos."""
    if actor.global_role not in ("root", "admin", "support"):
        return None, (jsonify({"error": "No tienes permiso para crear usuarios cliente"}), 403)

    client_id = data.get("client_id")
    client_role = data.get("client_role")

    if not client_id or not client_role:
        return None, (jsonify({"error": "Datos incompletos"}), 400)

    if client_role not in ("owner", "finops_admin", "viewer"):
        return None, (jsonify({"error": "client_role inválido"}), 400)

    client = Client.query.get(client_id)
    if not client:
        return None, (jsonify({"error": "Cliente no existe"}), 404)

    user = User(
        email=email,
        contact_name=contact_name,
        global_role=None,
        client_id=client_id,
        client_role=client_role,
        is_active=True,
        force_password_change=force_change,
    )
    return user, None


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
        "mfa_enabled": getattr(row, "mfa_enabled", False),
        "mfa_confirmed_at": getattr(row, "mfa_confirmed_at", None).isoformat()
        if getattr(row, "mfa_confirmed_at", None) else None,
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
