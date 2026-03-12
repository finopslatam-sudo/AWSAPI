from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class RDSRules:

    # =====================================================
    # ENTRYPOINT
    # =====================================================
    @staticmethod
    def run_all(client_id: int):

        total = 0

        total += RDSRules.public_access_rule(client_id)
        total += RDSRules.backup_retention_rule(client_id)
        total += RDSRules.encryption_rule(client_id)
        total += RDSRules.gp2_storage_rule(client_id)
        total += RDSRules.multi_az_rule(client_id)

        return total

    # =====================================================
    # PUBLIC ACCESS
    # =====================================================
    @staticmethod
    def public_access_rule(client_id: int):

        return RDSRules._evaluate_rule(
            client_id,
            condition=lambda r: r.resource_metadata.get("publicly_accessible"),
            finding_type="RDS_PUBLIC_ACCESS",
            severity="HIGH",
            message="RDS instance is publicly accessible.",
            savings=0
        )

    # =====================================================
    # BACKUP RETENTION
    # =====================================================
    @staticmethod
    def backup_retention_rule(client_id: int):

        return RDSRules._evaluate_rule(
            client_id,
            condition=lambda r: r.resource_metadata.get("backup_retention", 0) == 0,
            finding_type="RDS_NO_BACKUP_RETENTION",
            severity="HIGH",
            message="Backup retention is disabled (0 days).",
            savings=0
        )

    # =====================================================
    # ENCRYPTION
    # =====================================================
    @staticmethod
    def encryption_rule(client_id: int):

        return RDSRules._evaluate_rule(
            client_id,
            condition=lambda r: not r.resource_metadata.get("encrypted", False),
            finding_type="RDS_NOT_ENCRYPTED",
            severity="HIGH",
            message="RDS storage encryption is disabled.",
            savings=0
        )

    # =====================================================
    # GP2 STORAGE
    # =====================================================
    @staticmethod
    def gp2_storage_rule(client_id: int):

        return RDSRules._evaluate_rule(
            client_id,
            condition=lambda r: r.resource_metadata.get("storage_type") == "gp2",
            finding_type="RDS_GP2_STORAGE",
            severity="MEDIUM",
            message="RDS instance uses gp2 storage. Consider migrating to gp3.",
            savings=10
        )

    # =====================================================
    # MULTI-AZ
    # =====================================================
    @staticmethod
    def multi_az_rule(client_id: int):

        return RDSRules._evaluate_rule(
            client_id,
            condition=lambda r: not r.resource_metadata.get("multi_az", False),
            finding_type="RDS_MULTI_AZ_DISABLED",
            severity="MEDIUM",
            message="Multi-AZ is disabled. High availability not ensured.",
            savings=0
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENT)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="RDS",
            resource_type="DBInstance",
            is_active=True
        ).all()

        findings_created = 0

        for resource in resources:

            existing = AWSFinding.query.filter_by(
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
                    created = AWSFinding.upsert_finding(
                        client_id=client_id,
                        aws_account_id=resource.aws_account_id,
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        region=resource.region,
                        aws_service="RDS",
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