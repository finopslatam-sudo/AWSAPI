import boto3
from datetime import datetime, timedelta
from src.models.aws_finding import AWSFinding
from src.models.aws_account import AWSAccount
from src.aws.sts_service import STSService


class CoverageEngine:

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
            session_name="finops-coverage"
        )

        session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

        ce = session.client("ce", region_name="us-east-1")

        end = datetime.utcnow().date()
        start = end - timedelta(days=30)

        coverage = ce.get_reservation_coverage(
            TimePeriod={
                "Start": str(start),
                "End": str(end)
            },
            GroupBy=[
                {"Type": "DIMENSION", "Key": "SERVICE"}
            ]
        )

        total = 0

        for group in coverage.get("CoveragesByTime", []):

            for service in group.get("Groups", []):

                coverage_pct = float(
                    service["Coverage"]["CoveragePercentage"]
                )

                service_name = service["Attributes"]["SERVICE"]

                if coverage_pct < 70:

                    AWSFinding.upsert_finding(
                        client_id=client_id,
                        aws_account_id=aws_account.id,
                        resource_id=service_name,
                        resource_type="Coverage",
                        finding_type="LOW_RI_COVERAGE",
                        severity="HIGH",
                        message=f"RI coverage for {service_name}: {coverage_pct}%",
                        estimated_monthly_savings=None
                    )

                    total += 1

        return total