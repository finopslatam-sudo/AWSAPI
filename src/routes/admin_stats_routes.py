from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.models.client import Client
from src.models.subscription import ClientSubscription
from src.models.plan import Plan

admin_stats_bp = Blueprint("admin_stats", __name__, url_prefix="/api/admin")

@admin_stats_bp.route("/stats", methods=["GET"])
@jwt_required()
def admin_stats():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or user.global_role not in ["root", "support"]:
        return jsonify({"msg": "Unauthorized"}), 403

    return jsonify({
        "totals": {
            "users": User.query.count(),
            "clients": Client.query.count(),
            "subscriptions": ClientSubscription.query.count(),
            "plans": Plan.query.count()
        }
    }), 200
