from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class ELBRules:

    @staticmethod
    def run_all(client_id: int):
        return ELBRules.no_targets_rule(client_id)

    # =====================================================
    # LOAD BALANCER SIN TARGETS / INSTANCIAS
    # =====================================================
    @staticmethod
    def no_targets_rule(client_id: int):

        finding_type = "ELB_NO_TARGETS"
        severity = "HIGH"
        message = "Load Balancer sin target groups ni instancias registradas; AWS lo sigue facturando por hora aunque no reciba tráfico."
        savings = 18.0

        resources = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="ELB",
            is_active=True
        ).all()

        findings_created = 0

        for resource in resources:
            metadata = resource.resource_metadata or {}
            is_idle = (
                metadata.get("target_group_count") == 0
                or metadata.get("instance_count") == 0
            ) if ("target_group_count" in metadata or "instance_count" in metadata) else False

            existing = AWSFinding.query.filter_by(
                client_id=client_id,
                resource_id=resource.resource_id,
                finding_type=finding_type
            ).first()

            if is_idle:
                if existing:
                    existing.resolved = False
                    existing.message = message
                    existing.severity = severity
                    existing.estimated_monthly_savings = savings
                else:
                    created = AWSFinding.upsert_finding(
                        client_id=client_id,
                        aws_account_id=resource.aws_account_id,
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        region=resource.region,
                        aws_service="ELB",
                        finding_type=finding_type,
                        severity=severity,
                        message=message,
                        estimated_monthly_savings=savings
                    )
                    if created:
                        findings_created += 1
            else:
                if existing and not existing.resolved:
                    existing.resolved = True

        return findings_created
