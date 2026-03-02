import boto3
from datetime import datetime, timedelta
from src.models.aws_account import AWSAccount
from src.aws.sts_service import STSService


class RIService:

    @staticmethod
    def get_ri_coverage(client_id: int):

        aws_account = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        ).first()

        if not aws_account:
            return {
                "coverage_percentage": 0,
                "period_days": 30
            }

        sts = STSService()

        credentials = sts.assume_role(
            role_arn=aws_account.role_arn,
            external_id=aws_account.external_id,
            session_name="finops-ri-coverage-api"
        )

        session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

        ce = session.client("ce", region_name="us-east-1")

        end = datetime.utcnow().date()
        start = end - timedelta(days=30)

        response = ce.get_reservation_coverage(
            TimePeriod={
                "Start": start.strftime("%Y-%m-%d"),
                "End": end.strftime("%Y-%m-%d")
            },
            Granularity="MONTHLY"
        )

        try:
            coverage_pct = float(
                response["Total"]["CoverageHours"]["CoverageHoursPercentage"]
            )
        except Exception:
            coverage_pct = 0

        return {
            "coverage_percentage": round(coverage_pct, 2),
            "period_days": 30
        }