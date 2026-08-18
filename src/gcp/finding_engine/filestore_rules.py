from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class FilestoreRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += FilestoreRules.tier_review_rule(client_id)
        total += FilestoreRules.no_labels_rule(client_id)
        return total

    @staticmethod
    def tier_review_rule(client_id: int):
        return FilestoreRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('tier') == 'ENTERPRISE',
            finding_type="FILESTORE_TIER_REVIEW",
            severity="MEDIUM",
            message="Instancia Filestore en tier Enterprise, el mas costoso; confirmar que el caso de uso lo requiere.",
            savings=0.0,
        )


    @staticmethod
    def no_labels_rule(client_id: int):
        return FilestoreRules._evaluate_rule(
            client_id,
            condition=lambda r: not (r.tags or {}),
            finding_type="FILESTORE_NO_LABELS",
            severity="LOW",
            message="Instancia Filestore sin labels; dificulta la atribucion de costos por equipo/proyecto.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="Filestore",
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
                        gcp_service="Filestore",
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
