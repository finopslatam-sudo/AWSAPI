from .base_audit import BaseAudit
from src.models.aws_finding import AWSFinding
from src.models.tag_policy import TagPolicy
from src.models.database import db


class TagAudit(BaseAudit):

    def run(self):
        findings_created = 0

        # 1️⃣ Obtener políticas del cliente
        policies = TagPolicy.query.filter_by(
            client_id=self.client_id,
            is_required=True
        ).all()

        if not policies:
            return 0

        required_tags = [p.tag_key for p in policies]

        ec2 = self.session.client("ec2")

        # 2️⃣ Revisar instancias EC2
        instances = ec2.describe_instances()

        for reservation in instances["Reservations"]:
            for instance in reservation["Instances"]:

                instance_tags = {
                    tag["Key"]: tag["Value"]
                    for tag in instance.get("Tags", [])
                }

                for required_tag in required_tags:

                    if required_tag not in instance_tags:

                        existing = AWSFinding.query.filter_by(
                            aws_account_id=self.aws_account.id,
                            resource_id=instance["InstanceId"],
                            finding_type="MISSING_TAG",
                            resolved=False
                        ).first()

                        if existing:
                            continue

                        finding = AWSFinding(
                            client_id=self.client_id,
                            aws_account_id=self.aws_account.id,
                            resource_id=instance["InstanceId"],
                            resource_type="EC2",
                            finding_type="MISSING_TAG",
                            severity="HIGH",
                            message=f"Missing required tag: {required_tag}",
                            estimated_monthly_savings=0
                        )

                        db.session.add(finding)
                        findings_created += 1

        db.session.commit()
        return findings_created
