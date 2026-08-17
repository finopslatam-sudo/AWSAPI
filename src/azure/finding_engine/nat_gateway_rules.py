from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class NATGatewayRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += NATGatewayRules.no_subnets_rule(client_id)
        total += NATGatewayRules.no_public_ip_rule(client_id)
        return total

    # =====================================================
    # SIN SUBNETS ASOCIADAS (equivalente a NAT_IDLE_GATEWAY de AWS)
    # =====================================================
    @staticmethod
    def no_subnets_rule(client_id: int):

        return NATGatewayRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("subnet_count") == 0,
            finding_type="NATGATEWAY_NO_SUBNETS",
            severity="HIGH",
            message="NAT Gateway sin subnets asociadas; sigue facturando por hora sin servir tráfico. Verificar si puede eliminarse.",
            savings=32.0,
        )

    # =====================================================
    # CON SUBNETS PERO SIN IP PÚBLICA (MAL CONFIGURADO)
    # =====================================================
    @staticmethod
    def no_public_ip_rule(client_id: int):

        return NATGatewayRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("subnet_count", 0) > 0
            and (r.resource_metadata or {}).get("public_ip_count") == 0,
            finding_type="NATGATEWAY_NO_PUBLIC_IP",
            severity="MEDIUM",
            message="NAT Gateway con subnets asociadas pero sin IP pública asignada; el tráfico saliente fallará. Revisar la configuración.",
            savings=0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="NATGateway",
            resource_type="NatGateway",
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
                        azure_service="NATGateway",
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
