from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class LoadBalancerRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += LoadBalancerRules.idle_standard_lb_rule(client_id)
        total += LoadBalancerRules.basic_sku_deprecated_rule(client_id)
        return total

    # =====================================================
    # STANDARD LB SIN BACKEND (SIGUE FACTURANDO SIN TRÁFICO)
    # =====================================================
    @staticmethod
    def idle_standard_lb_rule(client_id: int):

        return LoadBalancerRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("sku_name") == "Standard"
            and (r.resource_metadata or {}).get("total_backend_addresses") == 0,
            finding_type="LOADBALANCER_IDLE_NO_BACKEND",
            severity="HIGH",
            message="Standard Load Balancer sin destinos en sus backend pools; sigue facturando por hora y por regla de balanceo sin servir tráfico real.",
            savings=18.0,
        )

    # =====================================================
    # BASIC SKU (RETIRADO POR MICROSOFT — 30/SEP/2025)
    # =====================================================
    @staticmethod
    def basic_sku_deprecated_rule(client_id: int):

        return LoadBalancerRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("sku_name") == "Basic",
            finding_type="LOADBALANCER_BASIC_SKU_DEPRECATED",
            severity="MEDIUM",
            message="Load Balancer con SKU Basic; Microsoft lo retiró el 30 de septiembre de 2025. Migrar a Standard SKU antes de que deje de funcionar.",
            savings=0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="LoadBalancer",
            resource_type="LoadBalancer",
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
                        azure_service="LoadBalancer",
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
