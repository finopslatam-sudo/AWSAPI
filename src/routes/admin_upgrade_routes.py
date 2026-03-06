"""
ADMIN UPGRADE ROUTES
====================

Aprobación de solicitudes de upgrade de plan.
Solo admin/root.
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.database import db
from src.models.user import User
from src.models.plan import Plan
from src.models.subscription import ClientSubscription
from src.models.plan_upgrade_request import PlanUpgradeRequest

from datetime import datetime


admin_upgrade_bp = Blueprint(
    "admin_upgrade",
    __name__,
    url_prefix="/api/admin/upgrades"
)


# =========================================
# LISTAR SOLICITUDES
# =========================================

@admin_upgrade_bp.route("", methods=["GET"])
@jwt_required()
def list_upgrade_requests():

    admin = User.query.get(int(get_jwt_identity()))

    if not admin or admin.global_role not in ["admin", "root"]:
        return jsonify({"error": "Forbidden"}), 403

    requests = PlanUpgradeRequest.query.filter_by(
        status="PENDING"
    ).all()

    data = []

    for r in requests:

        data.append({
            "id": r.id,
            "client_id": r.client_id,
            "requested_plan": r.requested_plan,
            "requested_by_user_id": r.requested_by_user_id,
            "created_at": r.created_at
        })

    return jsonify({"data": data}), 200


# =========================================
# APROBAR UPGRADE
# =========================================

@admin_upgrade_bp.route("/<int:request_id>/approve", methods=["POST"])
@jwt_required()
def approve_upgrade(request_id):

    admin = User.query.get(int(get_jwt_identity()))

    if not admin or admin.global_role not in ["admin", "root"]:
        return jsonify({"error": "Forbidden"}), 403

    req = PlanUpgradeRequest.query.get(request_id)

    if not req:
        return jsonify({"error": "Request not found"}), 404

    if req.status != "PENDING":
        return jsonify({"error": "Already processed"}), 400

    # ============================
    # OBTENER PLAN
    # ============================

    plan = Plan.query.filter_by(code=req.requested_plan).first()

    if not plan:
        return jsonify({"error": "Invalid plan"}), 400

    subscription = ClientSubscription.query.filter_by(
        client_id=req.client_id,
        is_active=True
    ).first()

    if not subscription:
        return jsonify({"error": "Subscription not found"}), 404

    # ============================
    # ACTUALIZAR PLAN
    # ============================

    subscription.plan_id = plan.id

    req.status = "APPROVED"
    req.approved_by = admin.id
    req.approved_at = datetime.utcnow()

    db.session.commit()

    return jsonify({"status": "approved"}), 200