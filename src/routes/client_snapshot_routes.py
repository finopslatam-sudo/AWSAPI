from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.client_snapshot_service import ClientSnapshotService

snapshot_bp = Blueprint(
    "client_snapshots",
    __name__,
    url_prefix="/api/client/snapshots"
)


def get_client_id():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    return user.client_id


# =====================================================
# GET LATEST SNAPSHOT
# =====================================================
@snapshot_bp.route("/latest", methods=["GET"])
@jwt_required()
def latest_snapshot():

    client_id = get_client_id()

    data = ClientSnapshotService.get_latest_snapshot(client_id)

    if not data:
        return jsonify({"message": "No snapshots available"}), 404

    return jsonify(data), 200


# =====================================================
# GET SNAPSHOT HISTORY (PAGINATED)
# =====================================================
@snapshot_bp.route("/", methods=["GET"])
@jwt_required()
def list_snapshots():

    client_id = get_client_id()

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 30))

    data = ClientSnapshotService.list_snapshots(
        client_id=client_id,
        page=page,
        per_page=per_page
    )

    return jsonify(data), 200


# =====================================================
# GET TREND
# =====================================================
@snapshot_bp.route("/trend", methods=["GET"])
@jwt_required()
def get_trend():

    client_id = get_client_id()

    days = int(request.args.get("days", 30))

    data = ClientSnapshotService.get_trend(client_id, days)

    return jsonify(data), 200


# =====================================================
# GET DELTA
# =====================================================
@snapshot_bp.route("/delta", methods=["GET"])
@jwt_required()
def get_delta():

    client_id = get_client_id()

    data = ClientSnapshotService.get_delta(client_id)

    if not data:
        return jsonify({"message": "Not enough data to calculate delta"}), 404

    return jsonify(data), 200