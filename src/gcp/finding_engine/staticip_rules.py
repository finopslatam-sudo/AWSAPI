from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class StaticIPRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += StaticIPRules.unassociated_rule(client_id)
        total += StaticIPRules.no_labels_rule(client_id)
        return total

    @staticmethod
    def unassociated_rule(client_id: int):
        return StaticIPRules._evaluate_rule(
            client_id,
            condition=lambda r: not (r.resource_metadata or {}).get('users'),
            finding_type="STATICIP_UNASSOCIATED",
            severity="MEDIUM",
            message="IP estatica sin ninguna instancia/regla asociada; sigue facturando aunque no se use.",
            savings=3.6,
        )


    @staticmethod
    def no_labels_rule(client_id: int):
        return StaticIPRules._evaluate_rule(
            client_id,
            condition=lambda r: not (r.tags or {}),
            finding_type="STATICIP_NO_LABELS",
            severity="LOW",
            message="IP estatica sin labels; dificulta la atribucion de costos por equipo/proyecto.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="StaticIPs",
            resource_type="Address",
            is_active=True
        ).all()

        findings_created = 0

        for resource in resources:

            existing = GCPFinding.query.filter_by(
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
                    created = GCPFinding.upsert_finding(
                        client_id=client_id,
                        gcp_account_id=resource.gcp_account_id,
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        region=resource.region,
                        gcp_service="StaticIPs",
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
