import uuid
import os
import boto3
import re

from botocore.exceptions import ClientError

from src.models.aws_account import AWSAccount
from src.models.database import db
from src.aws.sts_service import STSService
from src.auth.plan_permissions import get_plan_limit


class AWSConnectionService:

    # =====================================================
    # GENERATE EXTERNAL ID
    # =====================================================

    @staticmethod
    def generate_external_id():
        """
        Generate secure ExternalId for cross-account access.
        """
        return str(uuid.uuid4())

    # =====================================================
    # BUILD CLOUDFORMATION URL
    # =====================================================

    @staticmethod
    def build_cloudformation_url(external_id: str):

        finops_account_id = os.getenv("FINOPS_AWS_ACCOUNT_ID")

        if not finops_account_id:
            raise RuntimeError(
                "FINOPS_AWS_ACCOUNT_ID environment variable not set"
            )

        template_url = (
            "https://api.finopslatam.com/api/client/aws/template"
        )

        return (
            "https://console.aws.amazon.com/cloudformation/home"
            "?region=us-east-1#/stacks/create/review"
            f"?templateURL={template_url}"
            f"&stackName=FinOpsLatamStack"
            f"&param_ExternalId={external_id}"
            f"&param_FinOpsAccountId={finops_account_id}"
        )

    # =====================================================
    # VALIDATE ROLE ARN
    # =====================================================

    @staticmethod
    def validate_role_arn(role_arn: str):

        pattern = r"^arn:aws:iam::\d{12}:role\/.+$"

        if not re.match(pattern, role_arn):
            raise ValueError("Invalid AWS Role ARN")

    # =====================================================
    # CHECK PLAN LIMIT
    # =====================================================

    @staticmethod
    def check_account_limit(client_id: int):

        limit = get_plan_limit(client_id, "aws_accounts")

        current_accounts = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        ).count()

        if current_accounts >= limit:

            raise RuntimeError(
                f"AWS account limit reached for your plan ({limit})."
            )

    # =====================================================
    # VALIDATE CONNECTION + SAVE ACCOUNT
    # =====================================================

    @staticmethod
    def validate_and_save_account(client_id, role_arn, external_id):

        # -----------------------------------------
        # Validate ARN
        # -----------------------------------------

        AWSConnectionService.validate_role_arn(role_arn)

        # -----------------------------------------
        # Plan limit
        # -----------------------------------------

        AWSConnectionService.check_account_limit(client_id)

        # -----------------------------------------
        # Assume Role
        # -----------------------------------------

        try:

            creds = STSService.assume_role(role_arn, external_id)

        except ClientError as e:

            raise RuntimeError(
                f"AWS STS AssumeRole failed: {str(e)}"
            )

        # -----------------------------------------
        # Create AWS session
        # -----------------------------------------

        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
        )

        sts = session.client("sts")

        try:

            identity = sts.get_caller_identity()

        except ClientError as e:

            raise RuntimeError(
                f"Failed to verify AWS identity: {str(e)}"
            )

        account_id = identity["Account"]

        # -----------------------------------------
        # Prevent duplicate accounts
        # -----------------------------------------

        existing = AWSAccount.query.filter_by(
            client_id=client_id,
            account_id=account_id
        ).first()

        if existing:
            return account_id

        # -----------------------------------------
        # Save account
        # -----------------------------------------

        aws_account = AWSAccount(
            client_id=client_id,
            account_id=account_id,
            account_name="Primary",
            role_arn=role_arn,
            external_id=external_id,
            is_active=True
        )

        try:

            db.session.add(aws_account)
            db.session.commit()

        except Exception:

            db.session.rollback()

            raise RuntimeError(
                "Database error while saving AWS account"
            )

        return account_id