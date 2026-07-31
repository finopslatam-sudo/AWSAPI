from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class Route53Rules:

    @staticmethod
    def run_all(client_id: int):
        return Route53Rules.unused_zone_rule(client_id)

    # =====================================================
    # HOSTED ZONE SIN REGISTROS PROPIOS (SOLO NS + SOA)
    # =====================================================
    @staticmethod
    def unused_zone_rule(client_id: int):

        finding_type = "ROUTE53_UNUSED_ZONE"
        severity = "LOW"
        message = "Hosted Zone de Route53 sin registros propios más allá de NS/SOA; sigue generando costo mensual fijo aunque no esté en uso."
        savings = 0.5

        resources = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="Route53",
            resource_type="HostedZone",
            is_active=True
        ).all()

        findings_created = 0

        for resource in resources:
            metadata = resource.resource_metadata or {}
            is_unused = (metadata.get("record_set_count") or 0) <= 2

            existing = AWSFinding.query.filter_by(
                client_id=client_id,
                resource_id=resource.resource_id,
                finding_type=finding_type
            ).first()

            if is_unused:
                if existing:
                    existing.resolved = False
                    existing.message = message
                    existing.severity = severity
                else:
                    created = AWSFinding.upsert_finding(
                        client_id=client_id,
                        aws_account_id=resource.aws_account_id,
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        region=resource.region,
                        aws_service="Route53",
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
