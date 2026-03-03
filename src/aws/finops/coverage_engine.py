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

        # ===============================
        # Assume Role
        # ===============================
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

        print("🔥 COVERAGE ENGINE RUNNING")

        # ===============================
        # GLOBAL RI COVERAGE (NO GroupBy)
        # ===============================
        response = ce.get_reservation_coverage(
            TimePeriod={
                "Start": start.strftime("%Y-%m-%d"),
                "End": end.strftime("%Y-%m-%d")
            },
            Granularity="MONTHLY"
        )

        total = 0

        try:
            coverage_pct = float(
                response["Total"]["CoverageHours"]["CoverageHoursPercentage"]
            )
        except Exception:
            return 0

        print(f"RI Coverage %: {coverage_pct}")

        # ===============================
        # Threshold
        # ===============================
        if coverage_pct < 70:

            AWSFinding.upsert_finding(
                client_id=client_id,
                aws_account_id=aws_account.id,
                resource_id="GLOBAL",
                resource_type="Account",
                aws_service="EC2",
                finding_type="LOW_RI_COVERAGE",
                severity="HIGH",
                message=f"Global RI coverage last 30 days: {round(coverage_pct, 2)}%",
                estimated_monthly_savings=200
            )

            total += 1

        return total