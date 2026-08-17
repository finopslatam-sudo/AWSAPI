from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class ContainerRegistryRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += ContainerRegistryRules.admin_user_enabled_rule(client_id)
        total += ContainerRegistryRules.public_network_access_rule(client_id)
        return total

    # =====================================================
    # ADMIN USER (CREDENCIAL COMPARTIDA) HABILITADO
    # =====================================================
    @staticmethod
    def admin_user_enabled_rule(client_id: int):

        return ContainerRegistryRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("admin_user_enabled") is True,
            finding_type="ACR_ADMIN_USER_ENABLED",
            severity="MEDIUM",
            message="El Container Registry tiene el usuario admin (credencial compartida) habilitado; Microsoft recomienda deshabilitarlo y usar identidades de Azure AD/Managed Identity en su lugar.",
            savings=0,
        )

    # =====================================================
    # ACCESO DE RED PÚBLICO HABILITADO
    # =====================================================
    @staticmethod
    def public_network_access_rule(client_id: int):

        return ContainerRegistryRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("public_network_access") == "Enabled",
            finding_type="ACR_PUBLIC_NETWORK_ACCESS",
            severity="HIGH",
            message="El Container Registry permite acceso de red público; restringir con Private Endpoint o reglas de firewall si no es necesario.",
            savings=0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="ContainerRegistry",
            resource_type="Registry",
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
                        azure_service="ContainerRegistry",
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
