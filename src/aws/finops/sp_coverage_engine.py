import boto3
from datetime import datetime, timedelta, timezone

from src.models.aws_account import AWSAccount
from src.models.aws_finding import AWSFinding
from src.aws.sts_service import STSService


class SavingsPlanCoverageEngine:

    @staticmethod
    def run(client_id):

        aws_account = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        ).first()

        if not aws_account:
            return 0

        sts = STSService()

        credentials = sts.assume_role(
            role_arn=aws_account.role_arn,
            external_id=aws_account.external_id,
            session_name="finops-sp-coverage"
        )

        session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

        ce = session.client("ce", region_name="us-east-1")

        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=30)

        try:

            response = ce.get_savings_plans_coverage(
                TimePeriod={
                    "Start": str(start),
                    "End": str(end)
                }
            )

        except Exception as e:
            print(f"[SP COVERAGE ERROR]: {str(e)}")
            return 0

        coverage_data = response.get("SavingsPlansCoverage", {})
        coverage_pct = float(
            coverage_data.get("CoveragePercentage", 0)
        )

        print(f"SP Coverage %: {coverage_pct}")

        total = 0

        if coverage_pct < 70:

            AWSFinding.upsert_finding(
                client_id=client_id,
                aws_account_id=aws_account.id,
                resource_id="GLOBAL_SP_COVERAGE",
                resource_type="SavingsPlanCoverage",
                finding_type="LOW_SP_COVERAGE",
                severity="HIGH",
                message=f"Savings Plans coverage last 30 days: {coverage_pct}%",
                estimated_monthly_savings=None
            )

            total += 1

        return total