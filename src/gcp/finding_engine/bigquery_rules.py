from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class BigQueryRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += BigQueryRules.no_table_expiration_rule(client_id)
        total += BigQueryRules.no_partition_expiration_rule(client_id)
        return total

    @staticmethod
    def no_table_expiration_rule(client_id: int):
        return BigQueryRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('default_table_expiration_ms') is None,
            finding_type="BIGQUERY_NO_TABLE_EXPIRATION",
            severity="MEDIUM",
            message="Dataset BigQuery sin expiracion por defecto de tablas; los datos se acumulan indefinidamente incrementando el costo de almacenamiento.",
            savings=0.0,
        )


    @staticmethod
    def no_partition_expiration_rule(client_id: int):
        return BigQueryRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('default_partition_expiration_ms') is None,
            finding_type="BIGQUERY_NO_PARTITION_EXPIRATION",
            severity="LOW",
            message="Dataset BigQuery sin expiracion por defecto de particiones.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="BigQuery",
            resource_type="Dataset",
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
                        gcp_service="BigQuery",
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
