from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class VMRules:

    @staticmethod
    def run_all(client_id: int):
        return VMRules.stopped_not_deallocated_rule(client_id)

    # =====================================================
    # VM "STOPPED" SIN DEALLOCATE (sigue facturando cómputo)
    # =====================================================
    # En Azure, a diferencia de AWS, apagar una VM desde el SO (o con
    # "Stop" sin "Deallocate") deja el estado en "stopped" pero el
    # cómputo se sigue facturando — solo "deallocated" libera el cómputo.
    # Es un error de FinOps clásico y específico de Azure.
    @staticmethod
    def stopped_not_deallocated_rule(client_id: int):

        return VMRules._evaluate_rule(
            client_id,
            condition=lambda r: r.state == "stopped",
            finding_type="VM_STOPPED_NOT_DEALLOCATED",
            severity="HIGH",
            message="VM detenida pero no 'deallocated'; Azure sigue facturando el cómputo. Usar 'Stop (Deallocate)' en vez de apagar desde el SO.",
            savings=20.0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="VirtualMachines",
            resource_type="VirtualMachine",
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
                        azure_service="VirtualMachines",
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
