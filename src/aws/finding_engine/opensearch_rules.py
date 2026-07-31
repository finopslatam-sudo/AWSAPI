from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class OpenSearchRules:

    @staticmethod
    def run_all(client_id: int):
        return OpenSearchRules.unencrypted_rule(client_id)

    # =====================================================
    # DOMINIO SIN ENCRIPTACIÓN EN REPOSO
    # =====================================================
    @staticmethod
    def unencrypted_rule(client_id: int):

        finding_type = "OPENSEARCH_UNENCRYPTED"
        severity = "HIGH"
        message = "Dominio de OpenSearch sin encriptación en reposo habilitada; riesgo de seguridad sobre los datos indexados."
        savings = 0

        resources = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="OpenSearch",
            resource_type="Domain",
            is_active=True
        ).all()

        findings_created = 0

        for resource in resources:
            metadata = resource.resource_metadata or {}
            is_unencrypted = not metadata.get("encryption_at_rest", False)

            existing = AWSFinding.query.filter_by(
                client_id=client_id,
                resource_id=resource.resource_id,
                finding_type=finding_type
            ).first()

            if is_unencrypted:
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
                        aws_service="OpenSearch",
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
