"""
CLIENT USERS SERVICE
====================

Servicios para gestión de usuarios dentro de un cliente.
"""

from src.models.user import User


def get_client_users(client_id: int):

    users = (
        User.query
        .filter(
            User.client_id == client_id,
            User.global_role.is_(None)
        )
        .order_by(User.id.asc())
        .all()
    )

    result = []

    for u in users:

        result.append({
            "id": u.id,
            "email": u.email,
            "contact_name": u.contact_name,
            "client_role": u.client_role,
            "is_active": u.is_active,
            "force_password_change": u.force_password_change
        })

    return result