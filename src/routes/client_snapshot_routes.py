from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from src.auth.decorators import require_client_user_role
from src.services.client_snapshot_service import ClientSnapshotService

snapshot_bp = Blueprint(
    "client_snapshots",
    __name__,
    url_prefix="/api/client/snapshots"
)


# =====================================================
# GET LATEST SNAPSHOT
# =====================================================
@snapshot_bp.route("/latest", methods=["GET"])
@jwt_required()
@require_client_user_role()
def latest_snapshot(user):

    data = ClientSnapshotService.get_latest_snapshot(user.client_id)

    if not data:
        return jsonify({"message": "No snapshots available"}), 404

    return jsonify(data), 200


# =====================================================
# GET SNAPSHOT HISTORY (PAGINATED)
# =====================================================
@snapshot_bp.route("/", methods=["GET"])
@jwt_required()
@require_client_user_role()
def list_snapshots(user):

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 30))

    data = ClientSnapshotService.list_snapshots(
        client_id=user.client_id,
        page=page,
        per_page=per_page
    )

    return jsonify(data), 200


# =====================================================
# GET TREND
# =====================================================
@snapshot_bp.route("/trend", methods=["GET"])
@jwt_required()
@require_client_user_role()
def get_trend(user):

    days = int(request.args.get("days", 30))

    data = ClientSnapshotService.get_trend(user.client_id, days)

    return jsonify(data), 200


# =====================================================
# GET DELTA
# =====================================================
@snapshot_bp.route("/delta", methods=["GET"])
@jwt_required()
@require_client_user_role()
def get_delta(user):

    data = ClientSnapshotService.get_delta(user.client_id)

    if not data:
        return jsonify({"message": "Not enough data to calculate delta"}), 404

    return jsonify(data), 200