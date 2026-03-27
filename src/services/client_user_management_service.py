"""
Client User Management Service
===============================
Lógica de negocio para gestión de usuarios dentro de una organización cliente.
"""

from src.models.user import User
from src.models.database import db
from src.services.password_service import generate_temp_password, get_temp_password_expiration
from src.services.user_events_service import on_admin_reset_password, on_user_deactivated, on_user_reactivated
from src.services.email_service import send_email
from src.services.email_templates import build_user_welcome_email
from src.auth.plan_permissions import get_plan_limit


def create_client_user(actor: User, name: str, email: str, role: str, password: str) -> dict:
    """Creates a new user in the actor's organization. Raises ValueError on validation errors."""
    current_users = User.query.filter(
        User.client_id == actor.client_id,
        User.global_role.is_(None)
    ).count()
    user_limit = get_plan_limit(actor.client_id, "users")
    if current_users >= user_limit:
        raise ValueError(f"user_limit_reached:{user_limit}")

    if User.query.filter_by(email=email).first():
        raise ValueError("email_exists")

    new_user = User(
        contact_name=name,
        email=email,
        client_id=actor.client_id,
        client_role=role,
        global_role=None,
        is_active=True,
        force_password_change=True,
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    try:
        send_email(
            to=email,
            subject="Bienvenido a FinOpsLatam",
            body=build_user_welcome_email(name=name, email=email, password=password),
        )
    except Exception as e:
        print("Error sending welcome email:", e)

    return {
        "id": new_user.id,
        "email": new_user.email,
        "contact_name": new_user.contact_name,
        "client_role": new_user.client_role,
    }


def update_client_user(actor: User, user_id: int, data: dict) -> dict:
    """Updates a user in the actor's organization. Raises ValueError on errors."""
    user = User.query.get(user_id)
    if not user:
        raise ValueError("not_found")
    if user.client_id != actor.client_id:
        raise ValueError("forbidden")

    user.contact_name = data.get("name", user.contact_name)
    user.email = data.get("email", user.email)
    user.client_role = data.get("role", user.client_role)
    db.session.commit()

    return {
        "id": user.id,
        "email": user.email,
        "contact_name": user.contact_name,
        "client_role": user.client_role,
    }


def deactivate_client_user(actor: User, user_id: int) -> User:
    """Soft-deletes a user. Raises ValueError on errors."""
    user = User.query.get(user_id)
    if not user:
        raise ValueError("not_found")
    if user.client_id != actor.client_id:
        raise ValueError("forbidden")
    if user.id == actor.id:
        raise ValueError("self_delete")

    user.is_active = False
    db.session.commit()
    return user


def reset_client_user_password(actor: User, user_id: int) -> tuple:
    """Resets password for a user in the actor's organization. Returns (user, temp_password)."""
    user = User.query.get(user_id)
    if not user:
        raise ValueError("not_found")
    if user.client_id != actor.client_id:
        raise ValueError("forbidden")

    temp_password = generate_temp_password()
    user.set_password(temp_password)
    user.force_password_change = True
    user.password_expires_at = get_temp_password_expiration()
    db.session.commit()
    return user, temp_password


def activate_client_user(actor: User, user_id: int) -> User:
    """Reactivates a user in the actor's organization."""
    user = User.query.get(user_id)
    if not user:
        raise ValueError("not_found")
    if user.client_id != actor.client_id:
        raise ValueError("forbidden")

    user.is_active = True
    db.session.commit()
    return user
