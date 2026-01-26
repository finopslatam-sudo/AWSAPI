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
print("🔥 ADMIN STATS SERVICE LOADED FROM:", get_admin_stats.__module__)


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
    Devuelve métricas globales del sistema para ROOT / ADMIN / SUPPORT.

    Contrato:
    {
        companies: {...},
        users: {...},
        plans: {...}
    }
    """

    user = User.query.get(int(get_jwt_identity()))

    # 🔐 ROOT / ADMIN / SUPPORT
    if not user or user.global_role not in ("root", "admin", "support"):
        return jsonify({"error": "Unauthorized"}), 403

    stats = get_admin_stats() or {}

    # 🛡️ Blindaje del contrato
    response = {
        "companies": stats.get("companies", {
            "total": 0,
            "inactive": 0,
        }),
        "users": stats.get("users", {
            "clients": 0,
            "admins": 0,
            "root": 0,
            "inactive": 0,
        }),
        "plans": stats.get("plans", {
            "in_use": 0,
            "usage": [],
        }),
    }

    return jsonify(response), 200
