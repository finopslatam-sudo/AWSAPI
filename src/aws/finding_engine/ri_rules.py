from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding
from src.models.database import db
from datetime import datetime


class ReservedInstanceRules:

    @staticmethod
    def unused_ri_rule(client_id):

        count = 0

        ris = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="ReservedInstances",
            is_active=True
        ).all()

        ec2_instances = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="EC2",
            is_active=True
        ).all()

        for ri in ris:

            ri_type = ri.resource_metadata.get("instance_type")

            matching = [
                i for i in ec2_instances
                if i.resource_metadata.get("instance_type") == ri_type
                and i.state == "running"
            ]

            if not matching:

                finding = AWSFinding(
                    client_id=client_id,
                    aws_account_id=ri.aws_account_id,
                    resource_id=ri.resource_id,
                    resource_type="ReservedInstance",
                    finding_type="RI_UNUSED",
                    severity="HIGH",
                    message=f"Reserved Instance for {ri_type} appears unused",
                    estimated_monthly_savings=100.0,
                    resolved=False,
                    detected_at=datetime.utcnow(),
                    created_at=datetime.utcnow()
                )

                db.session.add(finding)
                count += 1

        return count