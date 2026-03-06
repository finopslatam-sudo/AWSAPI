"""
ADMIN PLAN UPGRADE ROUTES
=========================

Administración de solicitudes de upgrade de plan.

Permite a usuarios global admin/root:

- Ver solicitudes pendientes
- Aprobar upgrades
- Rechazar upgrades
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.models.plan_upgrade_request import PlanUpgradeRequest
from src.models.subscription import ClientSubscription
from src.models.plan import Plan
from src.models.database import db

from src.services.email_service import send_email
from src.services.email_templates import build_plan_changed_email


admin_plan_upgrade_bp = Blueprint(
    "admin_plan_upgrades",
    __name__,
    url_prefix="/api/admin/upgrades"
)


# =====================================================
# GET /api/admin/upgrades
# LISTAR SOLICITUDES PENDIENTES
# =====================================================

@admin_plan_upgrade_bp.route("", methods=["GET"])
@jwt_required()
def list_upgrade_requests():

    actor = User.query.get(int(get_jwt_identity()))

    if not actor or actor.global_role not in ("root", "admin"):
        return jsonify({"error": "Forbidden"}), 403

    requests = (
        PlanUpgradeRequest.query
        .filter_by(status="PENDING")
        .order_by(PlanUpgradeRequest.created_at.desc())
        .all()
    )

    data = []

    for r in requests:

        data.append({
            "id": r.id,
            "client_id": r.client_id,
            "requested_plan": r.requested_plan,
            "requested_by_user_id": r.requested_by_user_id,
            "created_at": r.created_at.isoformat()
        })

    return jsonify({
        "data": data
    }), 200


# =====================================================
# POST /api/admin/upgrades/{id}/approve
# APRUEBA UPGRADE
# =====================================================

@admin_plan_upgrade_bp.route("/<int:request_id>/approve", methods=["POST"])
@jwt_required()
def approve_upgrade(request_id):

    actor = User.query.get(int(get_jwt_identity()))

    if not actor or actor.global_role not in ("root", "admin"):
        return jsonify({"error": "Forbidden"}), 403

    request_upgrade = PlanUpgradeRequest.query.get(request_id)

    if not request_upgrade:
        return jsonify({"error": "Request not found"}), 404

    if request_upgrade.status != "PENDING":
        return jsonify({"error": "Request already processed"}), 400


    # =====================================
    # OBTENER SUSCRIPCIÓN ACTUAL
    # =====================================

    subscription = (
        ClientSubscription.query
        .filter_by(
            client_id=request_upgrade.client_id,
            is_active=True
        )
        .first()
    )

    if not subscription:
        return jsonify({"error": "Subscription not found"}), 404


    current_plan = Plan.query.get(subscription.plan_id)

    new_plan = Plan.query.filter_by(
        code=request_upgrade.requested_plan
    ).first()

    if not new_plan:
        return jsonify({"error": "Plan not found"}), 400


    # =====================================
    # ACTUALIZAR PLAN
    # =====================================

    subscription.plan_id = new_plan.id


    # =====================================
    # ACTUALIZAR REQUEST
    # =====================================

    request_upgrade.status = "APPROVED"
    request_upgrade.reviewed_by_user_id = actor.id


    db.session.commit()


    # =====================================
    # EMAIL CLIENTE
    # =====================================

    user = User.query.get(request_upgrade.requested_by_user_id)

    if user:

        email_body = build_plan_changed_email(
            name=user.contact_name,
            old_plan_name=current_plan.name,
            new_plan_name=new_plan.name
        )

        send_email(
            to=user.email,
            subject="FinOpsLatam — Plan actualizado",
            body=email_body
        )


    return jsonify({
        "status": "approved",
        "new_plan": new_plan.name
    }), 200


# =====================================================
# POST /api/admin/upgrades/{id}/reject
# RECHAZA SOLICITUD
# =====================================================

@admin_plan_upgrade_bp.route("/<int:request_id>/reject", methods=["POST"])
@jwt_required()
def reject_upgrade(request_id):

    actor = User.query.get(int(get_jwt_identity()))

    if not actor or actor.global_role not in ("root", "admin"):
        return jsonify({"error": "Forbidden"}), 403

    request_upgrade = PlanUpgradeRequest.query.get(request_id)

    if not request_upgrade:
        return jsonify({"error": "Request not found"}), 404

    if request_upgrade.status != "PENDING":
        return jsonify({"error": "Request already processed"}), 400


    request_upgrade.status = "REJECTED"
    request_upgrade.reviewed_by_user_id = actor.id

    db.session.commit()


    return jsonify({
        "status": "rejected"
    }), 200