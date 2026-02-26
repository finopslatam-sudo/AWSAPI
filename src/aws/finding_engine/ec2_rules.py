from datetime import datetime
from sqlalchemy import and_
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class EC2Rules:

    @staticmethod
    def stopped_instances_rule(client_id: int):

        stopped_instances = AWSResourceInventory.query.filter(
            and_(
                AWSResourceInventory.client_id == client_id,
                AWSResourceInventory.service_name == "EC2",
                AWSResourceInventory.resource_type == "Instance",
                AWSResourceInventory.state == "stopped",
                AWSResourceInventory.is_active == True
            )
        ).all()

        findings_created = 0

        for instance in stopped_instances:

            created = AWSFinding.upsert_finding(
                client_id=client_id,
                aws_account_id=instance.aws_account_id,
                resource_id=instance.resource_id,
                resource_type="EC2",
                finding_type="STOPPED_INSTANCE",
                severity="MEDIUM",
                message="EC2 instance is stopped",
                estimated_monthly_savings=10.0
            )

            if created:
                findings_created += 1

        return findings_created