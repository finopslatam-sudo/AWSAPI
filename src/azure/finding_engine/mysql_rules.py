from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class MySQLRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += MySQLRules.public_network_access_rule(client_id)
        total += MySQLRules.backup_retention_low_rule(client_id)
        return total

    # =====================================================
    # ACCESO DE RED PÚBLICO HABILITADO
    # =====================================================
    @staticmethod
    def public_network_access_rule(client_id: int):

        return MySQLRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("public_network_access") == "Enabled",
            finding_type="MYSQL_PUBLIC_NETWORK_ACCESS",
            severity="HIGH",
            message="Flexible Server de MySQL con acceso de red público habilitado; restringir con reglas de firewall/VNet integration o deshabilitarlo si no es necesario.",
            savings=0,
        )

    # =====================================================
    # BACKUP RETENTION BAJO (< 7 DÍAS)
    # =====================================================
    @staticmethod
    def backup_retention_low_rule(client_id: int):

        return MySQLRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("backup_retention_days") is not None
            and r.resource_metadata.get("backup_retention_days") < 7,
            finding_type="MYSQL_BACKUP_RETENTION_LOW",
            severity="MEDIUM",
            message="Período de backup retention menor a 7 días; aumentar para tener mayor margen de recuperación ante una falla o borrado accidental.",
            savings=0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="MySQL",
            resource_type="FlexibleServer",
            is_active=True
        ).all()

        findings_created = 0

        for resource in resources:

            existing = AzureFinding.query.filter_by(
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
                    created = AzureFinding.upsert_finding(
                        client_id=client_id,
                        azure_account_id=resource.azure_account_id,
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        region=resource.region,
                        azure_service="MySQL",
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
