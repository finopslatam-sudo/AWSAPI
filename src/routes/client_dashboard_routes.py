from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.dashboard.facade import ClientDashboardFacade
from src.services.dashboard.risk_service import RiskService
from src.services.dashboard.governance_service import GovernanceService
from src.services.dashboard.trend_service import TrendService
from src.services.dashboard.remediation_service import RemediationService
from src.services.dashboard.roi_service import ROIService
from src.services.client_dashboard_service import ClientDashboardService
from src.auth.plan_permissions import has_feature
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

    data = ClientDashboardFacade.get_summary(client_id)

    return jsonify(data), 200


# =====================================================
# RISK
# =====================================================

@dashboard_bp.route("/risk", methods=["GET"])
@jwt_required()
def get_risk():

    client_id, error_response, status = require_client_id()

    if error_response:
        return error_response, status

    data = RiskService.get_risk_score(client_id)

    return jsonify(data), 200


@dashboard_bp.route("/risk-breakdown", methods=["GET"])
@jwt_required()
def get_risk_breakdown():

    client_id, error_response, status = require_client_id()

    if error_response:
        return error_response, status

    data = RiskService.get_risk_breakdown_by_service(client_id)

    return jsonify(data), 200


@dashboard_bp.route("/priority-services", methods=["GET"])
@jwt_required()
def get_priority_services():

    client_id, error_response, status = require_client_id()

    if error_response:
        return error_response, status

    data = RiskService.get_priority_services(client_id)

    return jsonify(data), 200


# =====================================================
# GOVERNANCE
# =====================================================

@dashboard_bp.route("/governance", methods=["GET"])
@jwt_required()
def get_governance():

    client_id, error_response, status = require_client_id()

    if error_response:
        return error_response, status

    # ==========================
    # PLAN FEATURE CHECK
    # ==========================

    if not has_feature(client_id, "gobernanza"):
        return jsonify({
            "error": "Governance requires Professional plan"
        }), 403

    data = GovernanceService.get_governance_score(client_id)

    return jsonify(data), 200


# =====================================================
# ROI
# =====================================================

@dashboard_bp.route("/roi", methods=["GET"])
@jwt_required()
def get_roi():

    client_id, error_response, status = require_client_id()

    if error_response:
        return error_response, status

    data = ROIService.get_roi_projection(client_id)

    return jsonify(data), 200


# =====================================================
# TREND
# =====================================================

@dashboard_bp.route("/trend", methods=["GET"])
@jwt_required()
def get_trend():

    client_id, error_response, status = require_client_id()

    if error_response:
        return error_response, status

    data = TrendService.get_risk_trend(client_id, 30)

    return jsonify(data), 200


# =====================================================
# REMEDIATION
# =====================================================

@dashboard_bp.route("/remediation", methods=["GET"])
@jwt_required()
def get_remediation():

    client_id, error_response, status = require_client_id()

    if error_response:
        return error_response, status

    data = RemediationService.get_remediation_metrics(client_id, 30)

    return jsonify(data), 200


# =====================================================
# COST
# =====================================================

@dashboard_bp.route("/cost", methods=["GET"])
@jwt_required()
def get_cost():

    client_id, error_response, status = require_client_id()

    if not has_feature(client_id, "costos"):
        return jsonify({
            "error": "Cost module not available"
        }), 403

    if error_response:
        return error_response, status

    data = ClientDashboardService.get_cost_data(client_id)

    return jsonify(data), 200


# =====================================================
# INVENTORY SUMMARY
# =====================================================

@dashboard_bp.route("/inventory", methods=["GET"])
@jwt_required()
def get_inventory():

    client_id, error_response, status = require_client_id()

    if error_response:
        return error_response, status

    data = ClientDashboardService.get_inventory_summary(client_id)

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