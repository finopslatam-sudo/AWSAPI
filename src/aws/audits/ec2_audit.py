from .base_audit import BaseAudit
from src.models.database import db
from .utils import create_finding_if_not_exists


class EC2Audit(BaseAudit):

    def run(self):
        ec2 = self.session.client("ec2")
        findings_created = 0
        active_problematic_instances = []

        instances = ec2.describe_instances()

        for reservation in instances["Reservations"]:
            for instance in reservation["Instances"]:

                if instance["State"]["Name"] == "stopped":

                    active_problematic_instances.append(instance["InstanceId"])

                    created = self.create_or_reopen_finding(
                        resource_id=instance["InstanceId"],
                        resource_type="EC2",
                        finding_type="STOPPED_INSTANCE",
                        severity="MEDIUM",
                        message="EC2 instance is stopped",
                        estimated_monthly_savings=10
                    )

                    if created:
                        findings_created += 1

        # Resolver instancias que ya no están detenidas
        self.resolve_missing_findings(
            active_resource_ids=active_problematic_instances,
            finding_type="STOPPED_INSTANCE"
        )

        db.session.commit()
        return findings_created
