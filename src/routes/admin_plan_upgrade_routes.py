"""
ADMIN PLAN UPGRADE ROUTES
=========================
Administración de solicitudes de upgrade de plan.
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from src.models.user import User
from src.models.plan_upgrade_request import PlanUpgradeRequest
from src.models.subscription import ClientSubscription
from src.models.plan import Plan
from src.models.client import Client
from src.models.database import db
from src.services.plan_upgrade_notifications import notify_upgrade_approved, notify_upgrade_rejected


admin_plan_upgrade_bp = Blueprint(
    "admin_plan_upgrades", __name__, url_prefix="/api/admin/upgrades"
)


def require_admin(user_id: int):
    actor = User.query.get(user_id)
    if not actor or actor.global_role not in ("root", "admin"):
        return None
    return actor


@admin_plan_upgrade_bp.route("", methods=["GET"])
@jwt_required()
def list_upgrade_requests():
    actor = require_admin(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Forbidden"}), 403

    requests = (
        PlanUpgradeRequest.query
        .filter_by(status="PENDING")
        .order_by(PlanUpgradeRequest.created_at.desc())
        .all()
    )

    data = []
    for r in requests:
        client = Client.query.get(r.client_id)
        user = User.query.get(r.requested_by_user_id)
        current_plan = None
        subscription = ClientSubscription.query.filter_by(client_id=r.client_id, is_active=True).first()
        if subscription:
            plan = Plan.query.get(subscription.plan_id)
            if plan:
                current_plan = plan.name
        plan_requested = Plan.query.filter_by(code=r.requested_plan).first()
        data.append({
            "id": r.id,
            "client_id": r.client_id,
            "company_name": client.company_name if client else None,
            "email": user.email if user else None,
            "current_plan": current_plan,
            "requested_plan": plan_requested.name if plan_requested else r.requested_plan,
            "created_at": r.created_at.isoformat(),
        })

    return jsonify({"data": data}), 200


@admin_plan_upgrade_bp.route("/<int:request_id>/approve", methods=["POST"])
@jwt_required()
def approve_upgrade(request_id):
    actor = require_admin(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Forbidden"}), 403

    request_upgrade = PlanUpgradeRequest.query.get(request_id)
    if not request_upgrade:
        return jsonify({"error": "Request not found"}), 404
    if request_upgrade.status != "PENDING":
        return jsonify({"error": "Request already processed"}), 400

    subscription = ClientSubscription.query.filter_by(
        client_id=request_upgrade.client_id, is_active=True
    ).first()
    if not subscription:
        return jsonify({"error": "Subscription not found"}), 404

    current_plan = Plan.query.get(subscription.plan_id)
    new_plan = Plan.query.filter_by(code=request_upgrade.requested_plan).first()
    if not new_plan:
        return jsonify({"error": "Plan not found"}), 400

    subscription.plan_id = new_plan.id
    request_upgrade.status = "APPROVED"
    request_upgrade.approved_by = actor.id
    request_upgrade.approved_at = datetime.utcnow()
    db.session.commit()

    notify_upgrade_approved(request_upgrade, current_plan, new_plan)

    return jsonify({"data": {"status": "approved", "new_plan": new_plan.name}}), 200


@admin_plan_upgrade_bp.route("/<int:request_id>/reject", methods=["POST"])
@jwt_required()
def reject_upgrade(request_id):
    actor = require_admin(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Forbidden"}), 403

    request_upgrade = PlanUpgradeRequest.query.get(request_id)
    if not request_upgrade:
        return jsonify({"error": "Request not found"}), 404
    if request_upgrade.status != "PENDING":
        return jsonify({"error": "Request already processed"}), 400

    request_upgrade.status = "REJECTED"
    request_upgrade.approved_by = actor.id
    request_upgrade.approved_at = datetime.utcnow()
    db.session.commit()

    notify_upgrade_rejected(request_upgrade)

    return jsonify({"status": "rejected"}), 200
