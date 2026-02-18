from .base_audit import BaseAudit
from botocore.exceptions import ClientError
from src.models.database import db


class S3Audit(BaseAudit):

    def run(self):
        s3 = self.session.client("s3")
        findings_created = 0
        active_buckets = []

        buckets = s3.list_buckets()

        for bucket in buckets["Buckets"]:

            bucket_name = bucket["Name"]

            try:
                lifecycle = s3.get_bucket_lifecycle_configuration(
                    Bucket=bucket_name
                )

                has_rules = bool(lifecycle.get("Rules"))

            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchLifecycleConfiguration":
                    has_rules = False
                else:
                    continue

            if not has_rules:

                active_buckets.append(bucket_name)

                created = self.create_or_reopen_finding(
                    resource_id=bucket_name,
                    resource_type="S3",
                    finding_type="NO_LIFECYCLE_POLICY",
                    severity="MEDIUM",
                    message="S3 bucket does not have lifecycle policy",
                    estimated_monthly_savings=2
                )

                if created:
                    findings_created += 1

        self.resolve_missing_findings(
            active_resource_ids=active_buckets,
            finding_type="NO_LIFECYCLE_POLICY"
        )

        db.session.commit()
        return findings_created
