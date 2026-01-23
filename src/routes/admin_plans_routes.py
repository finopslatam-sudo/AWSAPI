# =====================================================
# ADMIN PLANS ROUTES
# =====================================================
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.models.plan import Plan

admin_plans_bp = Blueprint(
    "admin_plans",
    __name__,
    url_prefix="/api/admin"
)

def register_admin_plans_routes(app):
    app.register_blueprint(admin_plans_bp)

@admin_plans_bp.route("/plans", methods=["GET"])
@jwt_required()
def list_plans():
    user = User.query.get(int(get_jwt_identity()))

    if not user or user.global_role not in ("root", "admin"):
        return jsonify({"error": "Unauthorized"}), 403

    plans = Plan.query.order_by(Plan.id.asc()).all()

    return jsonify({
        "plans": [
            {"id": p.id, "code": p.code, "name": p.name}
            for p in plans
        ]
    }), 200
