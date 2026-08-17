from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class ContainerInstanceRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += ContainerInstanceRules.public_ip_exposed_rule(client_id)
        total += ContainerInstanceRules.restart_policy_always_rule(client_id)
        return total

    # =====================================================
    # IP PÚBLICA EXPUESTA
    # =====================================================
    @staticmethod
    def public_ip_exposed_rule(client_id: int):

        return ContainerInstanceRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("ip_address_type") == "Public",
            finding_type="CONTAINERINSTANCES_PUBLIC_IP_EXPOSED",
            severity="MEDIUM",
            message="Container Group con IP pública expuesta; verificar si es necesario o si conviene usar una IP privada con VNet integration.",
            savings=0,
        )

    # =====================================================
    # RESTART POLICY "ALWAYS" (COSTO INDEFINIDO SI FALLA EN LOOP)
    # =====================================================
    @staticmethod
    def restart_policy_always_rule(client_id: int):

        return ContainerInstanceRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("restart_policy") == "Always",
            finding_type="CONTAINERINSTANCES_RESTART_POLICY_ALWAYS",
            severity="LOW",
            message="Container Group con restart policy 'Always'; si es un job puntual y no un servicio persistente, esto puede generar reinicios continuos y costo indefinido ante una falla. Evaluar 'OnFailure' o 'Never'.",
            savings=0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="ContainerInstances",
            resource_type="ContainerGroup",
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
                        azure_service="ContainerInstances",
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
