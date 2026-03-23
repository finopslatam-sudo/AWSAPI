import logging

from src.aws.scanners.shared import BaseScanner


logger = logging.getLogger(__name__)


class StorageScanner(BaseScanner):
    """Handles S3 buckets (global) and Savings Plans (global)."""

    # ------------------------------------------------------------------
    # S3 (GLOBAL SERVICE)
    # ------------------------------------------------------------------
    def scan_s3(self):
        s3 = self.aws_session.client("s3")
        response = s3.list_buckets()

        for bucket in response.get("Buckets", []):
            bucket_name = bucket["Name"]

            try:
                location = s3.get_bucket_location(Bucket=bucket_name)
                region = location.get("LocationConstraint") or "us-east-1"
            except Exception:
                region = "unknown"

            self.upsert_resource(
                service_name="S3",
                resource_type="Bucket",
                resource_id=bucket_name,
                region=region,
                state="active",
                tags={},
                resource_metadata={
                    "creation_date": str(bucket.get("CreationDate"))
                }
            )

    # ------------------------------------------------------------------
    # SAVINGS PLANS (GLOBAL SERVICE)
    # ------------------------------------------------------------------
    def scan_savings_plans(self, region):
        try:
            # Savings Plans API is always queried against us-east-1
            savings = self.aws_session.client(
                "savingsplans",
                region_name="us-east-1"
            )

            response = savings.describe_savings_plans()

            for plan in response.get("savingsPlans", []):
                self.upsert_resource(
                    service_name="SavingsPlans",
                    resource_type=plan.get("planType"),
                    resource_id=plan.get("savingsPlanArn"),
                    region="global",
                    state=plan.get("state"),
                    tags={},
                    resource_metadata={
                        "commitment": str(plan.get("commitment")),
                        "term_length": plan.get("termLengthInSeconds"),
                        "payment_option": plan.get("paymentOption"),
                        "start": str(plan.get("start")),
                        "end": str(plan.get("end")),
                    }
                )

        except Exception:
            logger.exception("Savings Plans scan failed")
            raise
