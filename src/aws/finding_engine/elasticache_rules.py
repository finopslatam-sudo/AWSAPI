from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class ElastiCacheRules:

    @staticmethod
    def run_all(client_id: int):
        return ElastiCacheRules.no_backup_rule(client_id)

    # =====================================================
    # REDIS SIN RESPALDO (SNAPSHOTS DESHABILITADOS)
    # =====================================================
    @staticmethod
    def no_backup_rule(client_id: int):

        finding_type = "ELASTICACHE_NO_BACKUP"
        severity = "MEDIUM"
        message = "Cluster ElastiCache (Redis) sin snapshots automáticos configurados; riesgo de pérdida de datos ante una falla."
        savings = 0

        resources = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="ElastiCache",
            resource_type="CacheCluster",
            is_active=True
        ).all()

        findings_created = 0

        for resource in resources:
            metadata = resource.resource_metadata or {}
            is_redis = "redis" in (metadata.get("engine") or "").lower()
            no_backup = (metadata.get("snapshot_retention_limit") or 0) == 0

            existing = AWSFinding.query.filter_by(
                client_id=client_id,
                resource_id=resource.resource_id,
                finding_type=finding_type
            ).first()

            if is_redis and no_backup:
                if existing:
                    existing.resolved = False
                    existing.message = message
                    existing.severity = severity
                else:
                    created = AWSFinding.upsert_finding(
                        client_id=client_id,
                        aws_account_id=resource.aws_account_id,
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        region=resource.region,
                        aws_service="ElastiCache",
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
