from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from src.models.database import db
from src.models.user import User
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding

client_inventory_bp = Blueprint(
    "client_inventory",
    __name__,
    url_prefix="/api/client"
)


# ======================================================
# UTIL — SAFE INT PARSER
# ======================================================

def safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ======================================================
# GET INVENTORY (ENTERPRISE CORRECTO)
# ======================================================

@client_inventory_bp.route("/inventory", methods=["GET"])
@jwt_required()
def get_inventory():

    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or not user.client_id:
        return jsonify({
            "status": "error",
            "message": "Invalid user"
        }), 400

    client_id = user.client_id

    # -----------------------------
    # Query Params seguros
    # -----------------------------

    service_filter = request.args.get("service")

    page = safe_int(request.args.get("page"), 1)
    per_page = safe_int(request.args.get("per_page"), 50)

    # Limitar per_page para evitar abuso
    per_page = min(max(per_page, 1), 200)

    # -----------------------------
    # Base Query
    # -----------------------------

    base_query = AWSResourceInventory.query.filter_by(
        client_id=client_id,
        is_active=True
    )

    if service_filter:
        base_query = base_query.filter(
            AWSResourceInventory.service_name == service_filter
        )

    # -----------------------------
    # Summary por servicio (CORRECTO)
    # -----------------------------

    summary_query = db.session.query(
        AWSResourceInventory.service_name,
        func.count(AWSResourceInventory.id)
    ).filter_by(
        client_id=client_id,
        is_active=True
    ).group_by(
        AWSResourceInventory.service_name
    ).all()

    summary = {
        service: count
        for service, count in summary_query
    }

    # -----------------------------
    # Paginación
    # -----------------------------

    pagination = base_query.order_by(
        AWSResourceInventory.service_name,
        AWSResourceInventory.resource_id
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    inventory_items = pagination.items

    # -----------------------------
    # Findings agregados (UNA sola query)
    # -----------------------------

    findings_agg = db.session.query(
        AWSFinding.resource_id,
        func.count(AWSFinding.id).label("count"),
        func.max(AWSFinding.severity).label("max_severity")
    ).filter_by(
        client_id=client_id,
        resolved=False
    ).group_by(
        AWSFinding.resource_id
    ).all()

    findings_map = {
        f.resource_id: {
            "count": f.count,
            "max_severity": f.max_severity
        }
        for f in findings_agg
    }

    # -----------------------------
    # Construcción respuesta
    # -----------------------------

    resources = []

    for item in inventory_items:

        finding_data = findings_map.get(item.resource_id)

        resources.append({
            "resource_id": item.resource_id,
            "service_name": item.service_name,
            "resource_type": item.resource_type,
            "region": item.region,
            "state": item.state,
            "has_findings": bool(finding_data),
            "findings_count": finding_data["count"] if finding_data else 0,
            "max_severity": finding_data["max_severity"] if finding_data else None,
            "tags": item.tags,
            "detected_at": item.detected_at,
            "last_seen_at": item.last_seen_at
        })

    return jsonify({
        "status": "ok",
        "data": {
            "summary": summary,
            "resources": resources,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": pagination.total,
                "pages": pagination.pages
            }
        }
    })


# ======================================================
# GET INVENTORY SERVICES (CARDS)
# ======================================================

@client_inventory_bp.route("/inventory/services", methods=["GET"])
@jwt_required()
def get_inventory_services():

    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or not user.client_id:
        return jsonify({
            "status": "error",
            "message": "Invalid user"
        }), 400

    client_id = user.client_id

    from src.services.inventory.inventory_service import InventoryService

    data = InventoryService.get_services_summary(client_id)

    return jsonify({
        "status": "ok",
        "data": data
    }), 200

# ======================================================
# GET INVENTORY RESOURCES (ENTERPRISE HARDENED)
# ======================================================

@client_inventory_bp.route("/inventory/resources", methods=["GET"])
@jwt_required()
def get_inventory_resources_by_service():

    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or not user.client_id:
        return jsonify({
            "status": "error",
            "message": "Invalid user"
        }), 400

    service_name = request.args.get("service")
    min_severity = request.args.get("min_severity")
    sort = request.args.get("sort", "risk_desc")

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))

    if not service_name:
        return jsonify({
            "status": "error",
            "message": "Missing service parameter"
        }), 400

    from src.services.inventory.inventory_service import InventoryService

    result = InventoryService.get_resources_by_service(
        client_id=user.client_id,
        service_name=service_name,
        min_severity=min_severity,
        sort=sort,
        page=page,
        per_page=per_page
    )

    return jsonify({
        "status": "ok",
        "data": result["items"],
        "pagination": result["pagination"]
    }), 200