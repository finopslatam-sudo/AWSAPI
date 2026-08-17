from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class StorageRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += StorageRules.public_blob_access_rule(client_id)
        total += StorageRules.https_not_enforced_rule(client_id)
        return total

    # =====================================================
    # ACCESO PÚBLICO A BLOBS HABILITADO
    # =====================================================
    @staticmethod
    def public_blob_access_rule(client_id: int):

        return StorageRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("allow_blob_public_access") is True,
            finding_type="STORAGE_PUBLIC_BLOB_ACCESS",
            severity="HIGH",
            message="Storage Account permite acceso público anónimo a blobs; riesgo de exposición de datos si algún contenedor se configura como público.",
            savings=0,
        )

    # =====================================================
    # HTTPS NO FORZADO (TRÁFICO SIN CIFRAR PERMITIDO)
    # =====================================================
    @staticmethod
    def https_not_enforced_rule(client_id: int):

        return StorageRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("supports_https_traffic_only") is False,
            finding_type="STORAGE_HTTPS_NOT_ENFORCED",
            severity="HIGH",
            message="Storage Account permite tráfico HTTP sin cifrar; habilitar 'Secure transfer required' para forzar HTTPS.",
            savings=0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="StorageAccounts",
            resource_type="StorageAccount",
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
                        azure_service="StorageAccounts",
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
