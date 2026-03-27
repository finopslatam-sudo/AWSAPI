from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from src.models.database import db
from src.models.user import User
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding
from src.auth.plan_permissions import has_feature

client_inventory_bp = Blueprint(
    "client_inventory", __name__, url_prefix="/api/client/inventory"
)
client_inventory_bp.strict_slashes = False


def safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_state(state):
    if not state:
        return {"raw": None, "label": "Desconocido", "category": "unknown"}
    mapping = {
        "running":   ("Operativo", "healthy"),
        "active":    ("Operativo", "healthy"),
        "in-use":    ("En Uso",    "healthy"),
        "available": ("Sin Uso",   "waste"),
        "stopped":   ("Detenido",  "warning"),
    }
    label, category = mapping.get(state.lower(), (state.capitalize(), "unknown"))
    return {"raw": state, "label": label, "category": category}


def require_assets_user(user_id):
    user = User.query.get(user_id)
    if not user or not user.client_id:
        return None, ({"status": "error", "message": "Invalid user"}, 400)
    if not has_feature(user.client_id, "assets"):
        return None, ({"status": "error", "message": "Feature not available in current plan"}, 403)
    return user, None


@client_inventory_bp.route("/", methods=["GET"], strict_slashes=False)
@jwt_required()
def get_inventory():
    user, err = require_assets_user(get_jwt_identity())
    if err:
        return jsonify(err[0]), err[1]

    client_id = user.client_id
    service_filter = request.args.get("service")
    aws_account_id = request.args.get("aws_account_id", type=int)
    page = safe_int(request.args.get("page"), 1)
    per_page = min(max(safe_int(request.args.get("per_page"), 50), 1), 200)

    base_query = AWSResourceInventory.query.filter_by(client_id=client_id, is_active=True)
    if aws_account_id:
        base_query = base_query.filter(AWSResourceInventory.aws_account_id == aws_account_id)
    if service_filter:
        base_query = base_query.filter(AWSResourceInventory.service_name == service_filter)

    summary_q = db.session.query(
        AWSResourceInventory.service_name, func.count(AWSResourceInventory.id)
    ).filter(AWSResourceInventory.client_id == client_id, AWSResourceInventory.is_active == True)
    if aws_account_id:
        summary_q = summary_q.filter(AWSResourceInventory.aws_account_id == aws_account_id)
    summary = {svc: cnt for svc, cnt in summary_q.group_by(AWSResourceInventory.service_name).all()}

    pagination = base_query.order_by(
        AWSResourceInventory.service_name, AWSResourceInventory.resource_id
    ).paginate(page=page, per_page=per_page, error_out=False)

    findings_q = db.session.query(
        AWSFinding.resource_id,
        func.count(AWSFinding.id).label("count"),
        func.max(AWSFinding.severity).label("max_severity"),
    ).filter_by(client_id=client_id, resolved=False)
    if aws_account_id:
        findings_q = findings_q.filter(AWSFinding.aws_account_id == aws_account_id)
    findings_map = {
        f.resource_id: {"count": f.count, "max_severity": f.max_severity}
        for f in findings_q.group_by(AWSFinding.resource_id).all()
    }

    resources = []
    for item in pagination.items:
        fd = findings_map.get(item.resource_id)
        if fd:
            sev = fd["max_severity"]
            risk_label = "High Risk" if sev == "HIGH" else ("Medium Risk" if sev == "MEDIUM" else "Low Risk")
        else:
            sev = None
            risk_label = "No Issues"
        resources.append({
            "resource_id": item.resource_id,
            "service_name": item.service_name,
            "resource_type": item.resource_type,
            "region": item.region,
            "state": normalize_state(item.state),
            "severity": sev,
            "risk_label": risk_label,
            "findings_count": fd["count"] if fd else 0,
            "tags": item.tags,
            "detected_at": item.detected_at,
            "last_seen_at": item.last_seen_at,
        })

    return jsonify({
        "status": "ok",
        "data": {
            "summary": summary,
            "resources": resources,
            "pagination": {
                "page": page, "per_page": per_page,
                "total": pagination.total, "pages": pagination.pages,
            },
        },
    })


@client_inventory_bp.route("/services", methods=["GET"])
@jwt_required()
def get_inventory_services():
    user, err = require_assets_user(get_jwt_identity())
    if err:
        return jsonify(err[0]), err[1]

    from src.services.inventory.inventory_service import InventoryService
    data = InventoryService.get_services_summary(client_id=user.client_id)
    return jsonify({"status": "ok", "data": data}), 200


@client_inventory_bp.route("/health", methods=["GET"])
@jwt_required()
def get_global_health_score():
    user, err = require_assets_user(get_jwt_identity())
    if err:
        return jsonify(err[0]), err[1]

    from src.services.inventory.inventory_service import InventoryService
    data = InventoryService.get_global_health_score(client_id=user.client_id)
    return jsonify({"status": "ok", "data": data}), 200
