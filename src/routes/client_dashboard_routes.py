from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from src.auth.decorators import require_client_user_role
from src.services.dashboard.facade import ClientDashboardFacade
from src.services.risk_snapshot_service import RiskSnapshotService

dashboard_bp = Blueprint(
    "client_dashboard",
    __name__,
    url_prefix="/api/client/dashboard"
)


# =====================================================
# FULL DASHBOARD (Single Call Enterprise)
# =====================================================
@dashboard_bp.route("/", methods=["GET"])
@jwt_required()
@require_client_user_role()
def get_full_dashboard(user):

    # =====================================================
    # OPTIONAL ACCOUNT FILTER
    # =====================================================

    aws_account_id = request.args.get("aws_account_id", type=int)

    data = ClientDashboardFacade.get_summary(
        user.client_id,
        aws_account_id
    )

    return jsonify(data), 200

# =====================================================
# LAST SCAN
# =====================================================

@dashboard_bp.route("/last-scan", methods=["GET"])
@jwt_required()
@require_client_user_role()
def get_last_scan(user):

    last_scan = RiskSnapshotService.get_last_scan(user.client_id)

    return jsonify({
        "last_scan": last_scan.isoformat() if last_scan else None
    }), 200
