from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from src.models.aws_account import AWSAccount
from src.aws.connector import AWSConnector
from src.models.database import db

aws_test_bp = Blueprint("aws_test", __name__, url_prefix="/api/aws")


@aws_test_bp.route("/test/<int:account_id>", methods=["POST"])
@jwt_required()
def test_connection(account_id):
    account = AWSAccount.query.get_or_404(account_id)

    connector = AWSConnector(
        role_arn=account.role_arn,
        external_id=account.external_id
    )

    connector.assume_role()

    sts = connector.get_client("sts")
    identity = sts.get_caller_identity()

    account.last_sync = db.func.now()
    db.session.commit()

    return jsonify({
        "status": "success",
        "account": identity
    })
