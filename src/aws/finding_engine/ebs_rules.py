from sqlalchemy import and_
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class EBSRules:

    @staticmethod
    def unattached_volumes_rule(client_id: int):

        unattached_volumes = AWSResourceInventory.query.filter(
            and_(
                AWSResourceInventory.client_id == client_id,
                AWSResourceInventory.service_name == "EBS",
                AWSResourceInventory.resource_type == "Volume",
                AWSResourceInventory.state == "available",
                AWSResourceInventory.is_active == True
            )
        ).all()

        findings_created = 0

        for volume in unattached_volumes:

            created = AWSFinding.upsert_finding(
                client_id=client_id,
                aws_account_id=volume.aws_account_id,
                resource_id=volume.resource_id,
                resource_type="Volume",
                region=volume.region,
                aws_service=volume.service_name,
                finding_type="UNATTACHED_VOLUME",
                severity="HIGH",
                message="EBS volume not attached to any instance",
                estimated_monthly_savings=5.0
            )

            if created:
                findings_created += 1

        return findings_created

    # =====================================================
    # SNAPSHOT HUÉRFANO (el volumen de origen ya no existe)
    # =====================================================
    @staticmethod
    def orphaned_snapshot_rule(client_id: int):

        finding_type = "EBS_ORPHANED_SNAPSHOT"
        severity = "LOW"
        message = "Snapshot de EBS cuyo volumen de origen ya no existe; sigue generando costo de almacenamiento."

        active_volume_ids = {
            v.resource_id
            for v in AWSResourceInventory.query.filter_by(
                client_id=client_id,
                service_name="EBS",
                resource_type="Volume",
                is_active=True
            ).all()
        }

        snapshots = AWSResourceInventory.query.filter(
            and_(
                AWSResourceInventory.client_id == client_id,
                AWSResourceInventory.service_name == "EBS",
                AWSResourceInventory.resource_type == "Snapshot",
                AWSResourceInventory.is_active == True
            )
        ).all()

        findings_created = 0

        for snapshot in snapshots:

            source_volume_id = (snapshot.resource_metadata or {}).get("volume_id")
            is_orphaned = source_volume_id not in active_volume_ids

            existing = AWSFinding.query.filter_by(
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
                    created = AWSFinding.upsert_finding(
                        client_id=client_id,
                        aws_account_id=snapshot.aws_account_id,
                        resource_id=snapshot.resource_id,
                        resource_type="Snapshot",
                        region=snapshot.region,
                        aws_service="EBS",
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