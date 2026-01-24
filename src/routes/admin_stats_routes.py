"""
ADMIN STATS ROUTES
=================

Endpoints de estadísticas globales para administración.
Garantiza contrato estable para el frontend AdminDashboard.
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.admin_stats_service import get_admin_stats

# =====================================================
# BLUEPRINT
# =====================================================

admin_stats_bp = Blueprint(
    "admin_stats",
    __name__,
    url_prefix="/api/admin"
)

# =====================================================
# ROUTES
# =====================================================

@admin_stats_bp.route("/stats", methods=["GET"])
@jwt_required()
def admin_stats():
    """
    Devuelve métricas globales del sistema para ROOT / ADMIN.

    Contrato garantizado:
    {
        total_users: number,
        active_users: number,
        inactive_users: number,
        users_by_plan: [{ plan: string, count: number }]
    }
    """

    user = User.query.get(int(get_jwt_identity()))

    # 🔐 Solo ROOT / ADMIN
    if not user or user.global_role not in ("root", "admin"):
        return jsonify({"error": "Unauthorized"}), 403

    raw_stats = get_admin_stats() or {}

    # 🛡️ Blindaje del contrato para frontend
    stats = {
        "total_users": raw_stats.get("total_users", 0),
        "active_users": raw_stats.get("active_users", 0),
        "inactive_users": raw_stats.get("inactive_users", 0),
        "users_by_plan": raw_stats.get("users_by_plan") or [],
    }

    return jsonify(stats), 200
