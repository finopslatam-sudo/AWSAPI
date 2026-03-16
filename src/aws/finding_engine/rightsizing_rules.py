from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class RightsizingRules:

    @staticmethod
    def ec2_oversized_rule(client_id):

        count = 0

        oversized_types = [
            "m5.4xlarge",
            "m5.2xlarge",
            "c5.4xlarge",
            "r5.4xlarge"
        ]

        instances = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="EC2",
            is_active=True
        ).all()

        for instance in instances:

            instance_type = instance.resource_metadata.get("instance_type")
            state = instance.state

            if state != "running":
                continue

            if instance_type in oversized_types:

                created = AWSFinding.upsert_finding(
                    client_id=client_id,
                    aws_account_id=instance.aws_account_id,
                    resource_id=instance.resource_id,
                    resource_type="Instance",
                    region=instance.region,
                    aws_service=instance.service_name,
                    finding_type="RIGHTSIZING_OPPORTUNITY",
                    severity="MEDIUM",
                    message=f"Instance {instance.resource_id} may be oversized ({instance_type})",
                    estimated_monthly_savings=50.0
                )

                if created:
                    count += 1

        return count
