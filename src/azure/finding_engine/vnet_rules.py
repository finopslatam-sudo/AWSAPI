from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class VNetRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += VNetRules.ddos_protection_enabled_rule(client_id)
        total += VNetRules.no_subnets_rule(client_id)
        return total

    # =====================================================
    # DDOS PROTECTION STANDARD HABILITADO (COSTO FIJO ALTO)
    # =====================================================
    # DDoS Protection Standard tiene un costo fijo mensual elevado
    # (del orden de miles de USD/mes) — a diferencia del DDoS Protection
    # Basic, que viene incluido gratis en toda VNet. Es un hallazgo de
    # revisión de alto impacto específico de Azure, sin equivalente
    # directo en el resto del catálogo ya cubierto.
    @staticmethod
    def ddos_protection_enabled_rule(client_id: int):

        return VNetRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("ddos_protection_enabled") is True,
            finding_type="VNET_DDOS_PROTECTION_STANDARD_ENABLED",
            severity="MEDIUM",
            message="DDoS Protection Standard habilitado en esta VNet; tiene un costo fijo mensual elevado. Revisar si es realmente necesario o si el DDoS Protection Basic (gratuito, incluido por defecto) es suficiente.",
            savings=0,
        )

    # =====================================================
    # VNET SIN SUBNETS (POSIBLE RECURSO HUÉRFANO)
    # =====================================================
    @staticmethod
    def no_subnets_rule(client_id: int):

        return VNetRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("subnet_count") == 0,
            finding_type="VNET_NO_SUBNETS",
            severity="LOW",
            message="Virtual Network sin subnets configuradas; probablemente es un recurso huérfano que puede eliminarse.",
            savings=0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="VirtualNetwork",
            resource_type="VirtualNetwork",
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
                        azure_service="VirtualNetwork",
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
