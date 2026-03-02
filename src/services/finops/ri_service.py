import boto3
from datetime import datetime, timedelta
from botocore.exceptions import BotoCoreError, ClientError

from src.models.aws_account import AWSAccount
from src.aws.sts_service import STSService


class RIService:

    PERIOD_DAYS = 30

    @staticmethod
    def get_ri_coverage(client_id: int):

        aws_account = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        ).first()

        if not aws_account:
            return {
                "coverage_percentage": 0.0,
                "period_days": RIService.PERIOD_DAYS,
                "has_reserved_instances": False,
                "has_data": False,
                "error": "No active AWS account configured"
            }

        try:
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
            start = end - timedelta(days=RIService.PERIOD_DAYS)

            response = ce.get_reservation_coverage(
                TimePeriod={
                    "Start": start.strftime("%Y-%m-%d"),
                    "End": end.strftime("%Y-%m-%d")
                },
                Granularity="MONTHLY"
            )

            total_block = response.get("Total", {})
            coverage_hours = total_block.get("CoverageHours", {})

            coverage_percentage = float(
                coverage_hours.get("CoverageHoursPercentage", 0)
            )

            total_covered_hours = float(
                coverage_hours.get("CoverageHours", 0)
            )

            has_reserved_instances = total_covered_hours > 0

            return {
                "coverage_percentage": round(coverage_percentage, 2),
                "period_days": RIService.PERIOD_DAYS,
                "has_reserved_instances": has_reserved_instances,
                "has_data": True,
                "error": None
            }

        except (BotoCoreError, ClientError) as e:
            return {
                "coverage_percentage": 0.0,
                "period_days": RIService.PERIOD_DAYS,
                "has_reserved_instances": False,
                "has_data": False,
                "error": str(e)
            }