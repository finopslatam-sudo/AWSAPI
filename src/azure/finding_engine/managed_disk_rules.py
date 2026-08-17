from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class ManagedDiskRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += ManagedDiskRules.unattached_rule(client_id)
        total += ManagedDiskRules.zrs_review_rule(client_id)
        return total

    # =====================================================
    # DISCO SIN ADJUNTAR (equivalente a UNATTACHED_VOLUME de AWS)
    # =====================================================
    @staticmethod
    def unattached_rule(client_id: int):

        return ManagedDiskRules._evaluate_rule(
            client_id,
            condition=lambda r: r.state == "Unattached",
            finding_type="MANAGEDDISK_UNATTACHED",
            severity="HIGH",
            message="Managed Disk no adjunto a ninguna VM; sigue generando costo de almacenamiento.",
            savings=5.0,
        )

    # =====================================================
    # REDUNDANCIA ZRS (MÁS COSTOSA QUE LRS)
    # =====================================================
    @staticmethod
    def zrs_review_rule(client_id: int):

        return ManagedDiskRules._evaluate_rule(
            client_id,
            condition=lambda r: "ZRS" in ((r.resource_metadata or {}).get("sku_name") or ""),
            finding_type="MANAGEDDISK_ZRS_REVIEW",
            severity="LOW",
            message="Disco con redundancia Zone-Redundant Storage (ZRS), más costosa que LRS; verificar si la resiliencia zonal es realmente necesaria para este disco.",
            savings=0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="ManagedDisks",
            resource_type="Disk",
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
                        azure_service="ManagedDisks",
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
