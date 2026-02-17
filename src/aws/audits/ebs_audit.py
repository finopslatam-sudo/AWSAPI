from .base_audit import BaseAudit
from src.models.database import db
from .utils import create_finding_if_not_exists


class EBSAudit(BaseAudit):

    def run(self):
        ec2 = self.session.client("ec2")
        findings_created = 0

        volumes = ec2.describe_volumes()

        for v in volumes["Volumes"]:

            if v["State"] == "available":

                created = create_finding_if_not_exists(
                    client_id=self.client_id,
                    aws_account_id=self.aws_account.id,
                    resource_id=v["VolumeId"],
                    resource_type="EBS",
                    finding_type="UNATTACHED_VOLUME",
                    severity="HIGH",
                    message="EBS volume not attached to any instance",
                    estimated_savings=5
                )

                if created:
                    findings_created += 1

        db.session.commit()
        return findings_created
