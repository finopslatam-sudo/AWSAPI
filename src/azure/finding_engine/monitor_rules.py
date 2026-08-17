from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class MonitorRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += MonitorRules.unlimited_daily_quota_rule(client_id)
        total += MonitorRules.retention_high_rule(client_id)
        return total

    # =====================================================
    # SIN LÍMITE DE INGESTA DIARIA (DAILY CAP) — RIESGO DE
    # UN PICO DE COSTO INESPERADO, LA CAUSA #1 DE SORPRESAS
    # DE FACTURACIÓN EN AZURE MONITOR
    # =====================================================
    @staticmethod
    def unlimited_daily_quota_rule(client_id: int):

        return MonitorRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("daily_quota_gb") in (None, -1),
            finding_type="MONITOR_UNLIMITED_DAILY_QUOTA",
            severity="MEDIUM",
            message="Log Analytics Workspace sin límite de ingesta diaria (Daily Cap); un pico de logs (ej. un bug generando logs en loop) puede generar un costo inesperado muy alto. Configurar un Daily Cap.",
            savings=0,
        )

    # =====================================================
    # RETENCIÓN ALTA (> 90 DÍAS)
    # =====================================================
    @staticmethod
    def retention_high_rule(client_id: int):

        return MonitorRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("retention_in_days") is not None
            and r.resource_metadata.get("retention_in_days") > 90,
            finding_type="MONITOR_RETENTION_HIGH",
            severity="LOW",
            message="Retención de datos mayor a 90 días en el Log Analytics Workspace; evaluar si es necesaria o si conviene reducirla / archivar a un Storage Account más barato.",
            savings=0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="Monitor",
            resource_type="LogAnalyticsWorkspace",
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
                        azure_service="Monitor",
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
