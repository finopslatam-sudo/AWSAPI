from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.dashboard.facade import ClientDashboardFacade
from src.services.risk_snapshot_service import RiskSnapshotService

dashboard_bp = Blueprint(
    "client_dashboard",
    __name__,
    url_prefix="/api/client/dashboard"
)

# =====================================================
# INTERNAL CLIENT RESOLUTION (HARDENED)
# =====================================================

def get_client_id():
    identity = get_jwt_identity()

    if not identity:
        return None

    user = User.query.get(identity)

    if not user:
        return None

    return user.client_id


def require_client_id():
    client_id = get_client_id()

    if not client_id:
        return None, jsonify({"error": "Invalid token"}), 401

    return client_id, None, None


# =====================================================
# FULL DASHBOARD (Single Call Enterprise)
# =====================================================
@dashboard_bp.route("/", methods=["GET"])
@jwt_required()
def get_full_dashboard():

    client_id, error_response, status = require_client_id()

    if error_response:
        return error_response, status

    # =====================================================
    # OPTIONAL ACCOUNT FILTER
    # =====================================================

    aws_account_id = request.args.get("aws_account_id", type=int)

    data = ClientDashboardFacade.get_summary(
        client_id,
        aws_account_id
    )

    return jsonify(data), 200

# =====================================================
# LAST SCAN
# =====================================================

@dashboard_bp.route("/last-scan", methods=["GET"])
@jwt_required()
def get_last_scan():

    client_id, error_response, status = require_client_id()

    if error_response:
        return error_response, status

    last_scan = RiskSnapshotService.get_last_scan(client_id)

    return jsonify({
        "last_scan": last_scan.isoformat() if last_scan else None
    }), 200
