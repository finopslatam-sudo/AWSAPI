from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class AppServiceRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += AppServiceRules.https_only_disabled_rule(client_id)
        total += AppServiceRules.stopped_app_rule(client_id)
        return total

    # =====================================================
    # HTTPS ONLY DESHABILITADO
    # =====================================================
    @staticmethod
    def https_only_disabled_rule(client_id: int):

        return AppServiceRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("https_only") is False,
            finding_type="APPSERVICE_HTTPS_ONLY_DISABLED",
            severity="HIGH",
            message="Web App permite tráfico HTTP sin cifrar; habilitar 'HTTPS Only' en la configuración del sitio.",
            savings=0,
        )

    # =====================================================
    # WEB APP DETENIDA
    # =====================================================
    @staticmethod
    def stopped_app_rule(client_id: int):

        return AppServiceRules._evaluate_rule(
            client_id,
            condition=lambda r: r.state == "Stopped",
            finding_type="APPSERVICE_STOPPED",
            severity="LOW",
            message="Web App detenida; el App Service Plan asociado puede seguir facturando igual. Verificar si otras apps del plan justifican mantenerlo activo, o eliminar el plan si ya no se usa.",
            savings=0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="AppService",
            resource_type="WebApp",
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
                        azure_service="AppService",
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
