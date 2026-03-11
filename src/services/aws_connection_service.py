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
    # VALIDATE ACCOUNT ID
    # =====================================================

    @staticmethod
    def validate_account_id(account_id: str):

        pattern = r"^\d{12}$"

        if not re.match(pattern, account_id):
            raise ValueError("Invalid AWS Account ID")
        
    # =====================================================
    # BUILD ROLE ARN
    # =====================================================

    @staticmethod
    def build_role_arn(account_id: str):

        role_name = "FinOpsLatam-Audit-Role"

        return f"arn:aws:iam::{account_id}:role/{role_name}"

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
    def validate_and_save_account(client_id, account_id, external_id):

        # -----------------------------------------
        # Validate AWS Account ID
        # -----------------------------------------

        AWSConnectionService.validate_account_id(account_id)

        # -----------------------------------------
        # Build Role ARN automatically
        # -----------------------------------------

        role_arn = AWSConnectionService.build_role_arn(account_id)

        # -----------------------------------------
        # Validate generated ARN
        # -----------------------------------------

        AWSConnectionService.validate_role_arn(role_arn)

        # -----------------------------------------
        # Check plan limit
        # -----------------------------------------

        AWSConnectionService.check_account_limit(client_id)

        # -----------------------------------------
        # Assume Role via STS
        # -----------------------------------------

        print("Attempting STS AssumeRole")
        print("Role ARN:", role_arn)
        print("External ID:", external_id)

        try:

            creds = STSService.assume_role(role_arn, external_id)

        except ClientError as e:

            error_code = e.response["Error"]["Code"]

            if error_code == "AccessDenied":
                raise RuntimeError(
                    "AccessDenied: FinOpsLatam No puede asumir el rol. Verificar External ID y la política de confianza.."
                )

            raise RuntimeError(
                f"AWS STS error: {str(e)}"
            )

        # -----------------------------------------
        # Create AWS session with temporary creds
        # -----------------------------------------

        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
        )

        sts = session.client("sts")

        # -----------------------------------------
        # Verify AWS identity
        # -----------------------------------------

        try:

            identity = sts.get_caller_identity()

            verified_account_id = identity["Account"]

            print("Connected AWS account:", verified_account_id)

        except ClientError as e:

            raise RuntimeError(
                f"Failed to verify AWS identity: {str(e)}"
            )

        verified_account_id = identity["Account"]

        # -----------------------------------------
        # Extra safety check
        # Ensure role actually belongs to account
        # -----------------------------------------

        if verified_account_id != account_id:

            raise RuntimeError(
                "Account ID mismatch after STS validation"
            )

        # -----------------------------------------
        # Prevent duplicate accounts
        # -----------------------------------------

        existing = AWSAccount.query.filter_by(
            client_id=client_id,
            account_id=verified_account_id
        ).first()

        if existing:

            return verified_account_id

        # -----------------------------------------
        # Save account in database
        # -----------------------------------------

        aws_account = AWSAccount(
            client_id=client_id,
            account_id=verified_account_id,
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

        return verified_account_id
    