from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class ComputeRules:

    @staticmethod
    def run_all(client_id: int):
        return (
            ComputeRules.terminated_review_rule(client_id)
            + ComputeRules.no_labels_rule(client_id)
        )

    @staticmethod
    def terminated_review_rule(client_id: int):
        return ComputeRules._evaluate_rule(
            client_id,
            condition=lambda r: r.state == "TERMINATED",
            finding_type="INSTANCE_TERMINATED_REVIEW",
            severity="MEDIUM",
            message="Instancia Compute Engine detenida (TERMINATED); revisar si sigue siendo necesaria — los discos persistentes adjuntos se siguen facturando aunque el cómputo no.",
            savings=15.0,
        )

    @staticmethod
    def no_labels_rule(client_id: int):
        return ComputeRules._evaluate_rule(
            client_id,
            condition=lambda r: not (r.tags or {}),
            finding_type="INSTANCE_NO_LABELS",
            severity="LOW",
            message="Instancia Compute Engine sin labels; dificulta la atribución de costos por equipo/proyecto.",
            savings=0.0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="ComputeEngine",
            resource_type="Instance",
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
                        gcp_service="ComputeEngine",
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
