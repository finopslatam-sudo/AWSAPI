from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.finops.rightsizing_service import RightsizingService
from src.services.finops.ri_service import RIService
from src.services.finops.sp_service import SavingsPlansService
from src.auth.plan_permissions import has_feature

finops_bp = Blueprint(
    "client_finops",
    __name__,
    url_prefix="/api/client/finops"
)


def get_client_id():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    return user.client_id


# ===============================
# RIGHTSIZING
# ===============================
@finops_bp.route("/rightsizing", methods=["GET"])
@jwt_required()
def get_rightsizing():

    client_id = get_client_id()
    aws_account_id = request.args.get("aws_account_id", type=int)

    if not has_feature(client_id, "optimization"):
        return jsonify({
            "error": "Optimization requires Professional plan"
        }), 403

    data = RightsizingService.get_rightsizing_recommendations(
        client_id,
        aws_account_id
    )

    return jsonify(data), 200

# ===============================
# RI COVERAGE
# ===============================
@finops_bp.route("/ri-coverage", methods=["GET"])
@jwt_required()
def get_ri_coverage():

    client_id = get_client_id()
    aws_account_id = request.args.get("aws_account_id", type=int)

    if not has_feature(client_id, "optimization"):
        return jsonify({
            "error": "Optimization requires Professional plan"
        }), 403

    data = RIService.get_ri_coverage(client_id, aws_account_id)

    return jsonify(data), 200

# ===============================
# SP COVERAGE
# ===============================
@finops_bp.route("/sp-coverage", methods=["GET"])
@jwt_required()
def get_sp_coverage():

    client_id = get_client_id()
    aws_account_id = request.args.get("aws_account_id", type=int)

    if not has_feature(client_id, "optimization"):
        return jsonify({
            "error": "Optimization requires Professional plan"
        }), 403

    data = SavingsPlansService.get_sp_coverage(
        client_id,
        aws_account_id
    )

    return jsonify(data), 200
