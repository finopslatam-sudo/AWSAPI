from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class ServiceBusRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += ServiceBusRules.empty_namespace_rule(client_id)
        total += ServiceBusRules.tls_outdated_rule(client_id)
        return total

    @staticmethod
    def empty_namespace_rule(client_id: int):
        return ServiceBusRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('queue_count', 0) == 0 and (r.resource_metadata or {}).get('topic_count', 0) == 0,
            finding_type="SERVICEBUS_NAMESPACE_EMPTY",
            severity="MEDIUM",
            message="Namespace de Service Bus sin colas ni topics; sigue facturando su tier base sin mensajería activa.",
            savings=10.0,
        )


    @staticmethod
    def tls_outdated_rule(client_id: int):
        return ServiceBusRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('minimum_tls_version') not in ('1.2', None),
            finding_type="SERVICEBUS_TLS_OUTDATED",
            severity="MEDIUM",
            message="Namespace de Service Bus con una versión mínima de TLS desactualizada; actualizar a 1.2.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="ServiceBus",
            resource_type="Namespace",
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
                        azure_service="ServiceBus",
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
