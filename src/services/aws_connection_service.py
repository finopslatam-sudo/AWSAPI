import logging
import uuid

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

from src.models.aws_account import AWSAccount
from src.models.database import db
from src.cloud.aws_provider import AWSCloudProvider
from src.auth.plan_permissions import get_plan_limit
from src.aws.anomaly_monitor_service import AnomalyMonitorService
from src.services.default_policy_service import create_default_anomaly_policy
from src.services.aws_connection_helpers import (
    validate_account_id,
    validate_role_arn,
    build_role_arn,
    resolve_account_name,
    build_cloudformation_url,
)


class AWSConnectionService:

    @staticmethod
    def generate_external_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def build_cloudformation_url(external_id: str) -> str:
        return build_cloudformation_url(external_id)

    @staticmethod
    def check_account_limit(client_id: int):
        limit = get_plan_limit(client_id, "aws_accounts")
        current_accounts = AWSAccount.query.filter_by(
            client_id=client_id, is_active=True
        ).count()
        if current_accounts >= limit:
            raise RuntimeError(
                f"AWS account limit reached for your plan ({limit})."
            )

    @staticmethod
    def validate_and_save_account(client_id, account_id, external_id):
        validate_account_id(account_id)
        role_arn = build_role_arn(account_id)
        validate_role_arn(role_arn)
        AWSConnectionService.check_account_limit(client_id)

        logger.info("Attempting STS AssumeRole for account_id=%s", account_id)

        provider = AWSCloudProvider(role_arn=role_arn, external_id=external_id)
        try:
            provider.assume_role()
        except Exception as e:
            if "AccessDenied" in str(e):
                raise RuntimeError(
                    "AccessDenied: FinOpsLatam No puede asumir el rol. "
                    "Verificar External ID y la política de confianza.."
                )
            raise RuntimeError(f"AWS STS error: {str(e)}")

        session = provider.get_session()
        sts = provider.get_client("sts")

        try:
            identity = sts.get_caller_identity()
            verified_account_id = identity["Account"]
            logger.info("Connected AWS account: %s", verified_account_id)
        except ClientError as e:
            raise RuntimeError(f"Failed to verify AWS identity: {str(e)}")

        if verified_account_id != account_id:
            raise RuntimeError("Account ID mismatch after STS validation")

        existing = AWSAccount.query.filter_by(
            client_id=client_id, account_id=verified_account_id
        ).first()

        account_name = resolve_account_name(session, verified_account_id)

        if existing:
            logger.info("Updating existing AWS account name: %s", account_name)
            existing.account_name = account_name
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise RuntimeError("Database error while updating AWS account")
            return verified_account_id

        aws_account = AWSAccount(
            client_id=client_id,
            account_id=verified_account_id,
            account_name=account_name,
            role_arn=role_arn,
            external_id=external_id,
            is_active=True,
        )
        try:
            db.session.add(aws_account)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise RuntimeError("Database error while saving AWS account")

        monitor_arn = AnomalyMonitorService.create_from_session(session, verified_account_id)
        if monitor_arn:
            aws_account.anomaly_monitor_arn = monitor_arn
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

        try:
            create_default_anomaly_policy(client_id, aws_account)
        except Exception:
            logger.exception("[AWSConnection] Error creando política por defecto")

        return verified_account_id
