import boto3
from datetime import datetime, timedelta, timezone

from src.models.aws_account import AWSAccount
from src.models.aws_finding import AWSFinding
from src.aws.sts_service import STSService


class SavingsPlanCoverageEngine:

    MIN_COVERAGE_THRESHOLD = 70.0

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
                },
                GroupBy=[
                    {"Type": "DIMENSION", "Key": "SERVICE"}
                ]
            )
        except Exception as e:
            print(f"[SP COVERAGE ERROR]: {str(e)}")
            return 0

        total = 0

        for time_period in response.get("SavingsPlansCoverages", []):

            for group in time_period.get("Groups", []):

                service_name = group["Attributes"].get("SERVICE")
                coverage_pct = float(
                    group["Coverage"].get("CoveragePercentage", 0)
                )

                print(f"SP Coverage | {service_name}: {coverage_pct}%")

                if coverage_pct < SavingsPlanCoverageEngine.MIN_COVERAGE_THRESHOLD:

                    AWSFinding.upsert_finding(
                        client_id=client_id,
                        aws_account_id=aws_account.id,
                        resource_id=f"SP_{service_name}",
                        resource_type="SavingsPlanCoverage",
                        finding_type=f"LOW_SP_COVERAGE_{service_name.upper().replace(' ', '_')}",
                        severity="HIGH",
                        message=f"Savings Plans coverage for {service_name} last 30 days: {coverage_pct}%",
                        estimated_monthly_savings=None
                    )

                    total += 1

        return total