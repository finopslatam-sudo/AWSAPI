"""
ADMIN PLAN UPGRADE ROUTES
=========================

Administración de solicitudes de upgrade de plan.

Permite a usuarios global admin/root:

- Ver solicitudes pendientes
- Aprobar upgrades
- Rechazar upgrades
"""

from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.models.plan_upgrade_request import PlanUpgradeRequest
from src.models.subscription import ClientSubscription
from src.models.plan import Plan
from src.models.database import db

from src.services.email_service import send_email
from src.services.email_templates import (
    build_plan_changed_email,
    build_plan_upgrade_rejected_email
)

from src.models.client import Client
from src.models.notification import Notification
from datetime import datetime


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

        # CLIENTE
        client = Client.query.get(r.client_id)

        company_name = client.company_name if client else None

        # USUARIO QUE SOLICITÓ
        user = User.query.get(r.requested_by_user_id)

        email = user.email if user else None

        # PLAN ACTUAL
        current_plan = None

        subscription = (
            ClientSubscription.query
            .filter_by(client_id=r.client_id, is_active=True)
            .first()
        )

        if subscription:

            plan = Plan.query.get(subscription.plan_id)

            if plan:
                current_plan = plan.name

        # PLAN SOLICITADO
        plan_requested = Plan.query.filter_by(code=r.requested_plan).first()

        requested_plan = plan_requested.name if plan_requested else r.requested_plan

        data.append({
            "id": r.id,
            "client_id": r.client_id,
            "company_name": company_name,
            "email": email,
            "current_plan": current_plan,
            "requested_plan": requested_plan,
            "created_at": r.created_at.isoformat()
        })

    return jsonify({"data": data}), 200
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
    request_upgrade.approved_by = actor.id
    request_upgrade.approved_at = datetime.utcnow()


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


    # =====================================
    # NOTIFICACIONES IN-APP — USUARIOS DEL CLIENTE
    # =====================================
    try:
        client_users = User.query.filter_by(
            client_id=request_upgrade.client_id,
            is_active=True
        ).all()
        for cu in client_users:
            notif = Notification(
                user_id=cu.id,
                type="plan_upgrade_approved",
                title="¡Tu plan fue actualizado!",
                message=f"Tu plan ha sido actualizado a {new_plan.name}. Ya puedes disfrutar de las nuevas funcionalidades.",
            )
            db.session.add(notif)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error creando notificaciones de aprobación: {e}")

    return jsonify({
        "data": {
            "status": "approved",
            "new_plan": new_plan.name
        }
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
    request_upgrade.approved_by = actor.id
    request_upgrade.approved_at = datetime.utcnow()

    db.session.commit()

    user = User.query.get(request_upgrade.requested_by_user_id)

    if user:

        email_body = build_plan_upgrade_rejected_email(
            name=user.contact_name,
            plan_name=request_upgrade.requested_plan
        )

        send_email(
            to=user.email,
            subject="FinOpsLatam — Solicitud de upgrade rechazada",
            body=email_body
        )


    # =====================================
    # NOTIFICACIONES IN-APP — USUARIOS DEL CLIENTE
    # =====================================
    try:
        client_users = User.query.filter_by(
            client_id=request_upgrade.client_id,
            is_active=True
        ).all()
        plan_name = request_upgrade.requested_plan
        for cu in client_users:
            notif = Notification(
                user_id=cu.id,
                type="plan_upgrade_rejected",
                title="Solicitud de upgrade rechazada",
                message=f"Tu solicitud para cambiar al plan {plan_name} no fue aprobada. Contáctanos para más información.",
            )
            db.session.add(notif)
        db.session.commit()
    except Exception as e:
        print(f"Error creando notificaciones de rechazo: {e}")

    return jsonify({
        "status": "rejected"
    }), 200