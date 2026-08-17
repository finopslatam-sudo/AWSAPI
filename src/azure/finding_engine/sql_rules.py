from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class SQLRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += SQLRules.public_network_access_rule(client_id)
        total += SQLRules.tls_outdated_rule(client_id)
        return total

    # =====================================================
    # SQL SERVER CON ACCESO PÚBLICO HABILITADO
    # =====================================================
    @staticmethod
    def public_network_access_rule(client_id: int):

        return SQLRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("public_network_access") == "Enabled",
            finding_type="SQL_SERVER_PUBLIC_NETWORK_ACCESS",
            severity="HIGH",
            message="SQL Server con acceso de red público habilitado; restringir con reglas de firewall/Private Endpoint o deshabilitarlo si no es necesario.",
            savings=0,
        )

    # =====================================================
    # TLS MÍNIMO DESACTUALIZADO
    # =====================================================
    @staticmethod
    def tls_outdated_rule(client_id: int):

        return SQLRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("minimal_tls_version") not in ("1.2", None),
            finding_type="SQL_SERVER_TLS_OUTDATED",
            severity="MEDIUM",
            message="SQL Server permite versiones de TLS anteriores a 1.2; actualizar 'Minimum TLS Version' a 1.2.",
            savings=0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="SQLDatabase",
            resource_type="SqlServer",
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
                        azure_service="SQLDatabase",
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
