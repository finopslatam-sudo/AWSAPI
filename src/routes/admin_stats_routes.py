from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from src.models.user import User
from src.models.client import Client
from src.models.subscription import ClientSubscription
from src.models.plan import Plan

admin_stats_bp = Blueprint(
    "admin_stats",
    __name__,
    url_prefix="/api/admin"
)

@admin_stats_bp.route("/stats", methods=["GET"])
@jwt_required()
def admin_stats():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    # 🔐 Solo ROOT / SUPPORT
    if not user or user.global_role not in ("root", "support"):
        return jsonify({"msg": "Unauthorized"}), 403

    # =========================
    # USUARIOS
    # =========================
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    inactive_users = total_users - active_users

    # =========================
    # USUARIOS POR PLAN
    # =========================
    users_by_plan_query = (
        ClientSubscription.query
        .join(Plan, ClientSubscription.plan_id == Plan.id)
        .join(Client, ClientSubscription.client_id == Client.id)
        .with_entities(
            Plan.name.label("plan"),
            func.count(Client.id).label("count")
        )
        .group_by(Plan.name)
        .all()
    )

    users_by_plan = [
        {"plan": row.plan, "count": row.count}
        for row in users_by_plan_query
    ]

    # =========================
    # RESPONSE (FRONTEND READY)
    # =========================
    return jsonify({
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "users_by_plan": users_by_plan
    }), 200
