from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class SQLRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += SQLRules.public_no_ssl_rule(client_id)
        total += SQLRules.backup_disabled_rule(client_id)
        return total

    @staticmethod
    def public_no_ssl_rule(client_id: int):
        return SQLRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('require_ssl') is not True,
            finding_type="SQLINSTANCE_PUBLIC_NO_SSL",
            severity="HIGH",
            message="Instancia Cloud SQL sin SSL/TLS obligatorio en conexiones; riesgo de trafico sin cifrar.",
            savings=0.0,
        )


    @staticmethod
    def backup_disabled_rule(client_id: int):
        return SQLRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('backup_enabled') is not True,
            finding_type="SQLINSTANCE_BACKUP_DISABLED",
            severity="MEDIUM",
            message="Instancia Cloud SQL sin backups automaticos habilitados; riesgo de perdida de datos.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="CloudSQL",
            resource_type="DatabaseInstance",
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
                        gcp_service="CloudSQL",
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
