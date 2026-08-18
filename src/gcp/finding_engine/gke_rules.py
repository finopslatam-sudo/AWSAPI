from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class GKERules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += GKERules.autoscaling_disabled_rule(client_id)
        total += GKERules.no_release_channel_rule(client_id)
        return total

    @staticmethod
    def autoscaling_disabled_rule(client_id: int):
        return GKERules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('any_pool_without_autoscaling') is True,
            finding_type="GKE_AUTOSCALING_DISABLED",
            severity="LOW",
            message="Cluster GKE con al menos un node pool sin autoscaling; puede sobre-provisionar nodos innecesarios.",
            savings=0.0,
        )


    @staticmethod
    def no_release_channel_rule(client_id: int):
        return GKERules._evaluate_rule(
            client_id,
            condition=lambda r: not (r.resource_metadata or {}).get('release_channel'),
            finding_type="GKE_NO_RELEASE_CHANNEL",
            severity="MEDIUM",
            message="Cluster GKE no esta inscrito en un release channel; los parches de seguridad/version no se aplican automaticamente.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="GKE",
            resource_type="Cluster",
            is_active=True
        ).all()

        findings_created = 0

        for resource in resources:

            existing = GCPFinding.query.filter_by(
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
                    created = GCPFinding.upsert_finding(
                        client_id=client_id,
                        gcp_account_id=resource.gcp_account_id,
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        region=resource.region,
                        gcp_service="GKE",
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
