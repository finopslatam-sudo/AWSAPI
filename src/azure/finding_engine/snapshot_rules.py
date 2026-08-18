from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class SnapshotRules:

    @staticmethod
    def run_all(client_id: int):
        return SnapshotRules.orphaned_snapshot_rule(client_id)

    # =====================================================
    # SNAPSHOT HUÉRFANO (el disco de origen ya no existe)
    # =====================================================
    @staticmethod
    def orphaned_snapshot_rule(client_id: int):

        finding_type = "SNAPSHOT_ORPHANED"
        severity = "LOW"
        message = "Snapshot de Managed Disk cuyo disco de origen ya no existe; sigue generando costo de almacenamiento."

        active_disk_ids = {
            d.resource_id
            for d in AzureResourceInventory.query.filter_by(
                client_id=client_id,
                service_name="ManagedDisks",
                resource_type="Disk",
                is_active=True
            ).all()
        }

        snapshots = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="Snapshots",
            resource_type="Snapshot",
            is_active=True
        ).all()

        findings_created = 0

        for snapshot in snapshots:

            source_resource_id = (snapshot.resource_metadata or {}).get("source_resource_id")
            is_orphaned = source_resource_id not in active_disk_ids

            existing = AzureFinding.query.filter_by(
                client_id=client_id,
                resource_id=snapshot.resource_id,
                finding_type=finding_type
            ).first()

            if is_orphaned:

                if existing:
                    existing.resolved = False
                    existing.message = message
                    existing.severity = severity
                else:
                    created = AzureFinding.upsert_finding(
                        client_id=client_id,
                        azure_account_id=snapshot.azure_account_id,
                        resource_id=snapshot.resource_id,
                        resource_type="Snapshot",
                        region=snapshot.region,
                        azure_service="Snapshots",
                        finding_type=finding_type,
                        severity=severity,
                        message=message,
                        estimated_monthly_savings=0
                    )
                    if created:
                        findings_created += 1

            else:
                if existing and not existing.resolved:
                    existing.resolved = True

        return findings_created
