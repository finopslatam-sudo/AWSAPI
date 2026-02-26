from sqlalchemy import and_
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class EBSRules:

    @staticmethod
    def unattached_volumes_rule(client_id: int):

        unattached_volumes = AWSResourceInventory.query.filter(
            and_(
                AWSResourceInventory.client_id == client_id,
                AWSResourceInventory.service_name == "EBS",
                AWSResourceInventory.resource_type == "Volume",
                AWSResourceInventory.state == "available",
                AWSResourceInventory.is_active == True
            )
        ).all()

        findings_created = 0

        for volume in unattached_volumes:

            created = AWSFinding.upsert_finding(
                client_id=client_id,
                aws_account_id=volume.aws_account_id,
                resource_id=volume.resource_id,
                resource_type="EBS",
                finding_type="UNATTACHED_VOLUME",
                severity="HIGH",
                message="EBS volume not attached to any instance",
                estimated_monthly_savings=5.0
            )

            if created:
                findings_created += 1

        return findings_created