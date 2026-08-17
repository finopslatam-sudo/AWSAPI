from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class AKSRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += AKSRules.local_accounts_enabled_rule(client_id)
        total += AKSRules.autoscaling_disabled_rule(client_id)
        return total

    # =====================================================
    # CUENTAS LOCALES (NO-AAD) HABILITADAS
    # =====================================================
    @staticmethod
    def local_accounts_enabled_rule(client_id: int):

        return AKSRules._evaluate_rule(
            client_id,
            condition=lambda r: not (r.resource_metadata or {}).get("disable_local_accounts"),
            finding_type="AKS_LOCAL_ACCOUNTS_ENABLED",
            severity="MEDIUM",
            message="El clúster AKS permite cuentas locales (no-AAD) para autenticarse; deshabilitarlas y forzar auth vía Azure AD/Entra ID.",
            savings=0,
        )

    # =====================================================
    # AUTOSCALING DESHABILITADO EN ALGÚN NODE POOL
    # =====================================================
    @staticmethod
    def autoscaling_disabled_rule(client_id: int):

        return AKSRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("any_pool_without_autoscaling") is True,
            finding_type="AKS_AUTOSCALING_DISABLED",
            severity="LOW",
            message="Al menos un node pool del clúster no tiene autoscaling habilitado; sin autoscaler se corre el riesgo de sobreaprovisionar nodos que no se usan.",
            savings=0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="AKS",
            resource_type="ManagedCluster",
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
                        azure_service="AKS",
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
