"""
Thin orchestrator — preserves the original RightsizingEngine public API.
All implementation lives under src/aws/finops/rightsizing/.
"""
import boto3
from src.models.aws_account import AWSAccount
from src.aws.sts_service import STSService

from src.aws.finops.rightsizing.shared import (
    EC2_CPU_THRESHOLD,
    RDS_CPU_THRESHOLD,
    REDSHIFT_CPU_THRESHOLD,
    LAMBDA_LOW_INVOCATIONS_THRESHOLD,
    NAT_LOW_TRAFFIC_BYTES,
    CLOUDWATCH_MIN_STORED_BYTES,
    S3_MIN_BUCKET_SIZE_BYTES,
    S3_MIN_BUCKET_AGE_DAYS,
    resolve_finding,
    upsert_recommendation,
    get_metric_sum,
    get_metric_average,
)
from src.aws.finops.rightsizing.ec2 import evaluate_ec2, evaluate_ebs
from src.aws.finops.rightsizing.rds import evaluate_rds, evaluate_redshift
from src.aws.finops.rightsizing.lambda_ import evaluate_lambda
from src.aws.finops.rightsizing.storage import (
    evaluate_dynamodb,
    evaluate_cloudwatch,
    evaluate_s3,
)
from src.aws.finops.rightsizing.compute import (
    evaluate_ecs,
    evaluate_eks,
    evaluate_nat,
)


class RightsizingEngine:

    # =====================================================
    # CLASS-LEVEL THRESHOLDS (preserved for back-compat)
    # =====================================================
    EC2_CPU_THRESHOLD = EC2_CPU_THRESHOLD
    RDS_CPU_THRESHOLD = RDS_CPU_THRESHOLD
    REDSHIFT_CPU_THRESHOLD = REDSHIFT_CPU_THRESHOLD
    LAMBDA_LOW_INVOCATIONS_THRESHOLD = LAMBDA_LOW_INVOCATIONS_THRESHOLD
    NAT_LOW_TRAFFIC_BYTES = NAT_LOW_TRAFFIC_BYTES
    CLOUDWATCH_MIN_STORED_BYTES = CLOUDWATCH_MIN_STORED_BYTES
    S3_MIN_BUCKET_SIZE_BYTES = S3_MIN_BUCKET_SIZE_BYTES
    S3_MIN_BUCKET_AGE_DAYS = S3_MIN_BUCKET_AGE_DAYS

    # =====================================================
    # ORCHESTRATOR
    # =====================================================
    @staticmethod
    def run(client_id, aws_account_id=None):

        accounts_query = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        )

        if aws_account_id is not None:
            accounts_query = accounts_query.filter_by(id=aws_account_id)

        aws_accounts = accounts_query.all()

        if not aws_accounts:
            return 0

        sts = STSService()
        total = 0

        for aws_account in aws_accounts:
            credentials = sts.assume_role(
                role_arn=aws_account.role_arn,
                external_id=aws_account.external_id,
                session_name=f"finops-rightsizing-{aws_account.id}"
            )

            session = boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
            )

            total += evaluate_ec2(session, client_id, aws_account.id)
            total += evaluate_ebs(client_id, aws_account.id)
            total += evaluate_rds(session, client_id, aws_account.id)
            total += evaluate_lambda(session, client_id, aws_account.id)
            total += evaluate_dynamodb(session, client_id, aws_account.id)
            total += evaluate_cloudwatch(client_id, aws_account.id)
            total += evaluate_s3(session, client_id, aws_account.id)
            total += evaluate_ecs(session, client_id, aws_account.id)
            total += evaluate_eks(client_id, aws_account.id)
            total += evaluate_nat(session, client_id, aws_account.id)
            total += evaluate_redshift(session, client_id, aws_account.id)

        return total

    # =====================================================
    # SHARED HELPERS (delegated, preserved for back-compat)
    # =====================================================
    @staticmethod
    def _resolve_finding(client_id, aws_account_id, resource_id, finding_type):
        resolve_finding(client_id, aws_account_id, resource_id, finding_type)

    @staticmethod
    def _upsert_recommendation(
        client_id,
        aws_account_id,
        resource_id,
        resource_type,
        region,
        aws_service,
        finding_type,
        severity,
        message,
        estimated_monthly_savings
    ):
        upsert_recommendation(
            client_id=client_id,
            aws_account_id=aws_account_id,
            resource_id=resource_id,
            resource_type=resource_type,
            region=region,
            aws_service=aws_service,
            finding_type=finding_type,
            severity=severity,
            message=message,
            estimated_monthly_savings=estimated_monthly_savings
        )

    @staticmethod
    def _get_metric_sum(
        cloudwatch,
        namespace,
        metric_name,
        dimensions,
        start,
        end,
        period=86400
    ):
        return get_metric_sum(
            cloudwatch=cloudwatch,
            namespace=namespace,
            metric_name=metric_name,
            dimensions=dimensions,
            start=start,
            end=end,
            period=period
        )

    @staticmethod
    def _get_metric_average(
        cloudwatch,
        namespace,
        metric_name,
        dimensions,
        start,
        end,
        period=86400
    ):
        return get_metric_average(
            cloudwatch=cloudwatch,
            namespace=namespace,
            metric_name=metric_name,
            dimensions=dimensions,
            start=start,
            end=end,
            period=period
        )

    # =====================================================
    # SERVICE EVALUATORS (delegated, preserved for back-compat)
    # =====================================================
    @staticmethod
    def evaluate_ec2(session, client_id, aws_account_id):
        return evaluate_ec2(session, client_id, aws_account_id)

    @staticmethod
    def evaluate_ebs(client_id, aws_account_id):
        return evaluate_ebs(client_id, aws_account_id)

    @staticmethod
    def evaluate_rds(session, client_id, aws_account_id):
        return evaluate_rds(session, client_id, aws_account_id)

    @staticmethod
    def evaluate_lambda(session, client_id, aws_account_id):
        return evaluate_lambda(session, client_id, aws_account_id)

    @staticmethod
    def evaluate_dynamodb(session, client_id, aws_account_id):
        return evaluate_dynamodb(session, client_id, aws_account_id)

    @staticmethod
    def evaluate_cloudwatch(client_id, aws_account_id):
        return evaluate_cloudwatch(client_id, aws_account_id)

    @staticmethod
    def evaluate_s3(session, client_id, aws_account_id):
        return evaluate_s3(session, client_id, aws_account_id)

    @staticmethod
    def evaluate_ecs(session, client_id, aws_account_id):
        return evaluate_ecs(session, client_id, aws_account_id)

    @staticmethod
    def evaluate_eks(client_id, aws_account_id):
        return evaluate_eks(client_id, aws_account_id)

    @staticmethod
    def evaluate_nat(session, client_id, aws_account_id):
        return evaluate_nat(session, client_id, aws_account_id)

    @staticmethod
    def evaluate_redshift(session, client_id, aws_account_id):
        return evaluate_redshift(session, client_id, aws_account_id)
