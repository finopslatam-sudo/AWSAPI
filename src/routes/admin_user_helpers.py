# =====================================================
# ADMIN USERS — SHARED HELPERS
# =====================================================
# Shared permission helpers and view builder used by
# admin_users_routes.py and admin_user_access_routes.py

from src.models.user import User


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
