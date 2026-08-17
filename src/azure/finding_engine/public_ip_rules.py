from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class PublicIPRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += PublicIPRules.unassociated_rule(client_id)
        total += PublicIPRules.basic_sku_deprecated_rule(client_id)
        return total

    # =====================================================
    # IP PÚBLICA SIN ASOCIAR (equivalente a EIP_UNASSOCIATED de AWS)
    # =====================================================
    @staticmethod
    def unassociated_rule(client_id: int):

        return PublicIPRules._evaluate_rule(
            client_id,
            condition=lambda r: r.state == "unassociated",
            finding_type="PUBLICIP_UNASSOCIATED",
            severity="MEDIUM",
            message="Public IP no asociada a ningún recurso; sigue generando costo. Asociarla o liberarla.",
            savings=3.6,
        )

    # =====================================================
    # BASIC SKU (RETIRADO POR MICROSOFT — 30/SEP/2025)
    # =====================================================
    @staticmethod
    def basic_sku_deprecated_rule(client_id: int):

        return PublicIPRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("sku_name") == "Basic",
            finding_type="PUBLICIP_BASIC_SKU_DEPRECATED",
            severity="MEDIUM",
            message="Public IP con SKU Basic; Microsoft lo retiró el 30 de septiembre de 2025. Migrar a Standard SKU antes de que deje de funcionar.",
            savings=0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="PublicIP",
            resource_type="PublicIPAddress",
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
                        azure_service="PublicIP",
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
