from src.services.admin_users_service import get_all_users_with_plan


def get_admin_users():
    return get_all_users_with_plan()
