from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class KeyVaultRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += KeyVaultRules.purge_protection_disabled_rule(client_id)
        total += KeyVaultRules.public_network_access_rule(client_id)
        return total

    # =====================================================
    # PURGE PROTECTION DESHABILITADO
    # =====================================================
    @staticmethod
    def purge_protection_disabled_rule(client_id: int):

        return KeyVaultRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("purge_protection_enabled") is False,
            finding_type="KEYVAULT_PURGE_PROTECTION_DISABLED",
            severity="MEDIUM",
            message="Key Vault sin Purge Protection habilitado; sin esto, un secreto/key eliminado y purgado no se puede recuperar. Habilitarlo (no se puede deshabilitar una vez activado).",
            savings=0,
        )

    # =====================================================
    # ACCESO DE RED PÚBLICO (SIN RESTRICCIÓN)
    # =====================================================
    @staticmethod
    def public_network_access_rule(client_id: int):

        return KeyVaultRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("network_default_action") == "Allow",
            finding_type="KEYVAULT_PUBLIC_NETWORK_ACCESS",
            severity="HIGH",
            message="Key Vault sin restricciones de red (default action 'Allow'); restringir con Private Endpoint o reglas de firewall dado que almacena secretos/credenciales.",
            savings=0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="KeyVault",
            resource_type="Vault",
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
                        azure_service="KeyVault",
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
