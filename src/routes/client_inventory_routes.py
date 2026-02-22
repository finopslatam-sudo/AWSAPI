from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from src.models.database import db
from src.models.user import User
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding

client_inventory_bp = Blueprint("client_inventory", __name__, url_prefix="/api/client")


@client_inventory_bp.route("/inventory", methods=["GET"])
@jwt_required()
def get_inventory():

    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or not user.client_id:
        return jsonify({"status": "error", "message": "Invalid user"}), 400

    client_id = user.client_id

    # ================================
    # SUMMARY POR SERVICIO
    # ================================
    summary_query = db.session.query(
        AWSResourceInventory.resource_type,
        func.count(AWSResourceInventory.id)
    ).filter_by(
        client_id=client_id,
        is_active=True
    ).group_by(
        AWSResourceInventory.resource_type
    ).all()

    summary = {
        resource_type: count
        for resource_type, count in summary_query
    }

    # ================================
    # LISTADO DETALLADO
    # ================================
    resources = []

    inventory_items = AWSResourceInventory.query.filter_by(
        client_id=client_id,
        is_active=True
    ).all()

    for item in inventory_items:

        findings_count = AWSFinding.query.filter_by(
            client_id=client_id,
            resource_id=item.resource_id,
            resolved=False
        ).count()

        resources.append({
            "resource_id": item.resource_id,
            "resource_type": item.resource_type,
            "region": item.region,
            "state": item.state,
            "has_findings": findings_count > 0,
            "findings_count": findings_count,
            "tags": item.tags,
            "metadata": item.resource_metadata
        })

    return jsonify({
        "status": "ok",
        "data": {
            "summary": summary,
            "resources": resources
        }
    })