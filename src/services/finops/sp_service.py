import boto3
from datetime import datetime, timedelta, timezone
from botocore.exceptions import BotoCoreError, ClientError

from src.models.aws_account import AWSAccount
from src.aws.sts_service import STSService


class SavingsPlansService:

    PERIOD_DAYS = 30

    @staticmethod
    def get_sp_coverage(
        client_id: int,
        aws_account_id: int | None = None
    ):

        account_query = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        )

        if aws_account_id is not None:
            account_query = account_query.filter_by(id=aws_account_id)

        aws_account = account_query.first()

        if not aws_account:
            return {
                "period_days": SavingsPlansService.PERIOD_DAYS,
                "has_savings_plans": False,
                "has_data": False,
                "services": [],
                "error": "No active AWS account configured"
            }

        try:
            sts = STSService()

            credentials = sts.assume_role(
                role_arn=aws_account.role_arn,
                external_id=aws_account.external_id,
                session_name="finops-sp-coverage-api"
            )

            session = boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
            )

            ce = session.client("ce", region_name="us-east-1")

            end = datetime.now(timezone.utc).date()
            start = end - timedelta(days=SavingsPlansService.PERIOD_DAYS)

            response = ce.get_savings_plans_coverage(
                TimePeriod={
                    "Start": str(start),
                    "End": str(end)
                },
                GroupBy=[
                    {"Type": "DIMENSION", "Key": "SERVICE"}
                ]
            )

            results = []

            for period in response.get("SavingsPlansCoverages", []):
                for group in period.get("Groups", []):
                    service = group["Attributes"].get("SERVICE")
                    coverage = float(
                        group.get("Coverage", {}).get("CoveragePercentage", 0)
                    )

                    results.append({
                        "service": service,
                        "coverage_percentage": round(coverage, 2)
                    })

            return {
                "period_days": SavingsPlansService.PERIOD_DAYS,
                "has_savings_plans": len(results) > 0,
                "has_data": True,
                "services": results,
                "error": None
            }

        except (BotoCoreError, ClientError) as e:
            return {
                "period_days": SavingsPlansService.PERIOD_DAYS,
                "has_savings_plans": False,
                "has_data": False,
                "services": [],
                "error": str(e)
            }
