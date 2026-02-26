from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class ReservedInstanceRules:

    @staticmethod
    def unused_ri_rule(client_id):

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

        findings_created = 0

        for ri in ris:

            ri_type = ri.resource_metadata.get("instance_type")

            matching = [
                i for i in ec2_instances
                if i.resource_metadata.get("instance_type") == ri_type
                and i.state == "running"
            ]

            existing = AWSFinding.query.filter_by(
                client_id=client_id,
                resource_id=ri.resource_id,
                finding_type="RI_UNUSED"
            ).first()

            if not matching:

                if existing:
                    existing.resolved = False
                else:
                    created = AWSFinding.upsert_finding(
                        client_id=client_id,
                        aws_account_id=ri.aws_account_id,
                        resource_id=ri.resource_id,
                        resource_type="ReservedInstance",
                        finding_type="RI_UNUSED",
                        severity="HIGH",
                        message=f"Reserved Instance for {ri_type} appears unused",
                        estimated_monthly_savings=100.0
                    )
                    if created:
                        findings_created += 1
            else:
                if existing and not existing.resolved:
                    existing.resolved = True

        return findings_created