from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class LoadBalancerRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += LoadBalancerRules.no_backend_service_rule(client_id)
        total += LoadBalancerRules.legacy_scheme_rule(client_id)
        return total

    @staticmethod
    def no_backend_service_rule(client_id: int):
        return LoadBalancerRules._evaluate_rule(
            client_id,
            condition=lambda r: not (r.resource_metadata or {}).get('backend_service'),
            finding_type="LOADBALANCER_NO_BACKEND_SERVICE",
            severity="HIGH",
            message="Forwarding rule sin backend service asociado; el balanceador sigue facturando sin servir trafico real.",
            savings=18.0,
        )


    @staticmethod
    def legacy_scheme_rule(client_id: int):
        return LoadBalancerRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('load_balancing_scheme') == 'EXTERNAL',
            finding_type="LOADBALANCER_LEGACY_SCHEME",
            severity="LOW",
            message="Forwarding rule usa el esquema Network LB clasico (EXTERNAL); evaluar migrar al balanceador moderno para mejor costo/funcionalidad.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="LoadBalancing",
            resource_type="ForwardingRule",
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
                        gcp_service="LoadBalancing",
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
