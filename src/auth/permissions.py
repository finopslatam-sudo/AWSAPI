from src.models.user import User

def require_admin(user_id: int) -> User | None:
    """
    Compatibilidad temporal:
    Admin = staff interno (root o support)
    """
    user = User.query.get(user_id)

    if not user:
        return None

    if user.global_role not in ("root", "support"):
        return None

    return user
