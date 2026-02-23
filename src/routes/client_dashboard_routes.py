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

dashboard_bp = Blueprint("client_dashboard", __name__, url_prefix="/api/client/dashboard")


def get_client_id():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    return user.client_id


# =====================================================
# SUMMARY (Full Aggregated)
# =====================================================
@dashboard_bp.route("/summary", methods=["GET"])
@jwt_required()
def get_summary():
    client_id = get_client_id()
    data = ClientDashboardFacade.get_summary(client_id)
    return jsonify(data), 200


# =====================================================
# RISK
# =====================================================
@dashboard_bp.route("/risk", methods=["GET"])
@jwt_required()
def get_risk():
    client_id = get_client_id()
    data = RiskService.get_risk_score(client_id)
    return jsonify(data), 200


@dashboard_bp.route("/risk-breakdown", methods=["GET"])
@jwt_required()
def get_risk_breakdown():
    client_id = get_client_id()
    data = RiskService.get_risk_breakdown_by_service(client_id)
    return jsonify(data), 200


@dashboard_bp.route("/priority-services", methods=["GET"])
@jwt_required()
def get_priority_services():
    client_id = get_client_id()
    data = RiskService.get_priority_services(client_id)
    return jsonify(data), 200


# =====================================================
# GOVERNANCE
# =====================================================
@dashboard_bp.route("/governance", methods=["GET"])
@jwt_required()
def get_governance():
    client_id = get_client_id()
    data = GovernanceService.get_governance_score(client_id)
    return jsonify(data), 200


# =====================================================
# ROI
# =====================================================
@dashboard_bp.route("/roi", methods=["GET"])
@jwt_required()
def get_roi():
    client_id = get_client_id()
    data = ROIService.get_roi_projection(client_id)
    return jsonify(data), 200


# =====================================================
# TREND
# =====================================================
@dashboard_bp.route("/trend", methods=["GET"])
@jwt_required()
def get_trend():
    client_id = get_client_id()
    data = TrendService.get_risk_trend(client_id, 30)
    return jsonify(data), 200


# =====================================================
# REMEDIATION
# =====================================================
@dashboard_bp.route("/remediation", methods=["GET"])
@jwt_required()
def get_remediation():
    client_id = get_client_id()
    data = RemediationService.get_remediation_metrics(client_id, 30)
    return jsonify(data), 200


# =====================================================
# COST
# =====================================================
@dashboard_bp.route("/cost", methods=["GET"])
@jwt_required()
def get_cost():
    client_id = get_client_id()
    data = ClientDashboardService.get_cost_data(client_id)
    return jsonify(data), 200


# =====================================================
# INVENTORY SUMMARY
# =====================================================
@dashboard_bp.route("/inventory", methods=["GET"])
@jwt_required()
def get_inventory():
    client_id = get_client_id()
    data = ClientDashboardService.get_inventory_summary(client_id)
    return jsonify(data), 200