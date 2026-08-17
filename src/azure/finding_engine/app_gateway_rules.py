from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class AppGatewayRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += AppGatewayRules.no_backend_pool_rule(client_id)
        total += AppGatewayRules.autoscale_disabled_rule(client_id)
        return total

    # =====================================================
    # SIN DESTINOS EN BACKEND POOLS (SIGUE FACTURANDO)
    # =====================================================
    @staticmethod
    def no_backend_pool_rule(client_id: int):

        return AppGatewayRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("total_backend_addresses") == 0,
            finding_type="APPGATEWAY_NO_BACKEND_POOL",
            severity="HIGH",
            message="Application Gateway sin destinos en sus backend pools; sigue facturando por hora y por unidad de capacidad sin servir tráfico real.",
            savings=25.0,
        )

    # =====================================================
    # AUTOSCALING DESHABILITADO (CAPACIDAD FIJA)
    # =====================================================
    @staticmethod
    def autoscale_disabled_rule(client_id: int):

        return AppGatewayRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("autoscale_enabled") is False,
            finding_type="APPGATEWAY_AUTOSCALE_DISABLED",
            severity="MEDIUM",
            message="Application Gateway con capacidad fija (sin autoscaling); si el tráfico es variable, se puede estar sobreaprovisionando. Evaluar migrar a SKU v2 con autoscaling.",
            savings=0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="ApplicationGateway",
            resource_type="ApplicationGateway",
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
                        azure_service="ApplicationGateway",
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
