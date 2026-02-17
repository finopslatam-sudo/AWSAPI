from .base_audit import BaseAudit
from src.models.database import db
from .utils import create_finding_if_not_exists


class EC2Audit(BaseAudit):

    def run(self):
        ec2 = self.session.client("ec2")
        findings_created = 0

        instances = ec2.describe_instances()

        for reservation in instances["Reservations"]:
            for instance in reservation["Instances"]:

                if instance["State"]["Name"] == "stopped":

                    created = create_finding_if_not_exists(
                        client_id=self.client_id,
                        aws_account_id=self.aws_account.id,
                        resource_id=instance["InstanceId"],
                        resource_type="EC2",
                        finding_type="STOPPED_INSTANCE",
                        severity="MEDIUM",
                        message="EC2 instance is stopped",
                        estimated_savings=10
                    )

                    if created:
                        findings_created += 1

        db.session.commit()
        return findings_created
