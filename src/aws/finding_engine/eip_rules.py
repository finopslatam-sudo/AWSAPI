from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class EIPRules:

    @staticmethod
    def run_all(client_id: int):
        return EIPRules.unassociated_eip_rule(client_id)

    # =====================================================
    # ELASTIC IP SIN ASOCIAR
    # =====================================================
    @staticmethod
    def unassociated_eip_rule(client_id: int):

        return EIPRules._evaluate_rule(
            client_id,
            condition=lambda r: r.state == "unassociated",
            finding_type="EIP_UNASSOCIATED",
            severity="MEDIUM",
            message="Elastic IP no asociada a ninguna instancia; AWS la sigue facturando por hora.",
            savings=3.6,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="EIP",
            resource_type="ElasticIP",
            is_active=True
        ).all()

        findings_created = 0

        for resource in resources:

            existing = AWSFinding.query.filter_by(
                client_id=client_id,
                resource_id=resource.resource_id,
                finding_type=finding_type
            ).first()

            if condition(resource):

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
                        aws_service="EIP",
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
