"""
ADMIN STATS ROUTES
=================

Endpoints de estadísticas globales para administración.
Contrato estable para el frontend AdminDashboard (overview ejecutivo).
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.admin_overview_service import get_admin_overview

# Debug explícito de carga (solo logs, no afecta prod)
print("🔥 ADMIN OVERVIEW SERVICE LOADED FROM:", get_admin_overview.__module__)

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
    Devuelve métricas ejecutivas globales del sistema.

    Roles permitidos:
    - ROOT
    - ADMIN
    - SUPPORT

    Contrato:
    {
        companies: {
            total: number,
            inactive: number
        },
        users: {
            clients: number,
            admins: number,
            root: number,
            inactive: number
        },
        plans: {
            in_use: number,
            usage: [{ plan: string, count: number }]
        }
    }
    """

    user = User.query.get(int(get_jwt_identity()))

    # 🔐 Control de acceso
    if not user or user.global_role not in ("root", "admin", "support"):
        return jsonify({"error": "Unauthorized"}), 403

    stats = get_admin_overview()

    return jsonify(stats), 200
