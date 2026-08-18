from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class CloudRunRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += CloudRunRules.ingress_all_rule(client_id)
        total += CloudRunRules.no_max_instances_rule(client_id)
        return total

    @staticmethod
    def ingress_all_rule(client_id: int):
        return CloudRunRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('ingress') == 'INGRESS_TRAFFIC_ALL',
            finding_type="CLOUDRUN_INGRESS_ALL",
            severity="MEDIUM",
            message="Servicio Cloud Run acepta trafico de cualquier origen (ingress ALL); revisar si deberia restringirse a interno/Load Balancer.",
            savings=0.0,
        )


    @staticmethod
    def no_max_instances_rule(client_id: int):
        return CloudRunRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('max_instance_count') is None,
            finding_type="CLOUDRUN_NO_MAX_INSTANCES",
            severity="LOW",
            message="Servicio Cloud Run sin limite maximo de instancias configurado; riesgo de escalado descontrolado y facturacion inesperada.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="CloudRun",
            resource_type="Service",
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
                        gcp_service="CloudRun",
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
