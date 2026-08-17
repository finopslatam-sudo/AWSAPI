from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class FirewallRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += FirewallRules.no_ip_config_rule(client_id)
        total += FirewallRules.premium_tier_review_rule(client_id)
        return total

    # =====================================================
    # SIN IP CONFIGURADA (MAL CONFIGURADO, SIGUE FACTURANDO)
    # =====================================================
    @staticmethod
    def no_ip_config_rule(client_id: int):

        return FirewallRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("ip_configuration_count") == 0
            and not (r.resource_metadata or {}).get("has_hub_ip"),
            finding_type="FIREWALL_NO_IP_CONFIG",
            severity="HIGH",
            message="Azure Firewall sin configuración de IP; no puede filtrar tráfico pero sigue facturando por hora (costo significativo). Completar la configuración o eliminarlo.",
            savings=0,
        )

    # =====================================================
    # TIER PREMIUM (COSTO SIGNIFICATIVAMENTE MAYOR)
    # =====================================================
    @staticmethod
    def premium_tier_review_rule(client_id: int):

        return FirewallRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("sku_tier") == "Premium",
            finding_type="FIREWALL_PREMIUM_TIER_REVIEW",
            severity="LOW",
            message="Azure Firewall Premium tiene un costo significativamente mayor a Standard; verificar si las features Premium (IDPS, inspección TLS) son realmente necesarias.",
            savings=0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="Firewall",
            resource_type="AzureFirewall",
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
                        azure_service="Firewall",
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
