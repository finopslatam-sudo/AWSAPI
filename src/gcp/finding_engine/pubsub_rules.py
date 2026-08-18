from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class PubSubRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += PubSubRules.no_kms_encryption_rule(client_id)
        total += PubSubRules.no_labels_rule(client_id)
        return total

    @staticmethod
    def no_kms_encryption_rule(client_id: int):
        return PubSubRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('kms_key_name') is None,
            finding_type="PUBSUB_NO_KMS_ENCRYPTION",
            severity="MEDIUM",
            message="Topico Pub/Sub sin CMEK (clave gestionada por el cliente); usa solo cifrado por defecto de Google.",
            savings=0.0,
        )


    @staticmethod
    def no_labels_rule(client_id: int):
        return PubSubRules._evaluate_rule(
            client_id,
            condition=lambda r: not (r.tags or {}),
            finding_type="PUBSUB_NO_LABELS",
            severity="LOW",
            message="Topico Pub/Sub sin labels; dificulta la atribucion de costos por equipo/proyecto.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="PubSub",
            resource_type="Topic",
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
                        gcp_service="PubSub",
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
