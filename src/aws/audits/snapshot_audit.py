from .base_audit import BaseAudit
from src.models.database import db
from datetime import datetime, timedelta


class SnapshotAudit(BaseAudit):

    def run(self):
        ec2 = self.session.client("ec2")
        findings_created = 0
        active_snapshots = []

        threshold_date = datetime.utcnow() - timedelta(days=30)

        snapshots = ec2.describe_snapshots(OwnerIds=["self"])

        for snapshot in snapshots["Snapshots"]:

            start_time = snapshot["StartTime"].replace(tzinfo=None)

            if start_time < threshold_date:

                snapshot_id = snapshot["SnapshotId"]
                active_snapshots.append(snapshot_id)

                created = self.create_or_reopen_finding(
                    resource_id=snapshot_id,
                    resource_type="EBS_SNAPSHOT",
                    finding_type="OLD_SNAPSHOT",
                    severity="MEDIUM",
                    message="Snapshot older than 30 days",
                    estimated_monthly_savings=5
                )

                if created:
                    findings_created += 1

        self.resolve_missing_findings(
            active_resource_ids=active_snapshots,
            finding_type="OLD_SNAPSHOT"
        )

        db.session.commit()
        return findings_created
