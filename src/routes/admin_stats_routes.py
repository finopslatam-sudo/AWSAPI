"""
ADMIN STATS ROUTES
=================

Endpoints de estadísticas globales para administración.
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.admin_stats_service import get_admin_stats

admin_stats_bp = Blueprint(
    "admin_stats",
    __name__,
    url_prefix="/api/admin"
)


@admin_stats_bp.route("/stats", methods=["GET"])
@jwt_required()
def admin_stats():
    user = User.query.get(int(get_jwt_identity()))

    # 🔐 Solo ROOT / ADMIN
    if not user or user.global_role not in ("root", "admin"):
        return jsonify({"error": "Unauthorized"}), 403

    stats = get_admin_stats()

    return jsonify(stats), 200
