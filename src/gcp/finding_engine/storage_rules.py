from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class StorageRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += StorageRules.public_access_not_prevented_rule(client_id)
        total += StorageRules.uniform_access_disabled_rule(client_id)
        return total

    @staticmethod
    def public_access_not_prevented_rule(client_id: int):
        return StorageRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('public_access_prevention') != 'enforced',
            finding_type="BUCKET_PUBLIC_ACCESS_NOT_PREVENTED",
            severity="HIGH",
            message="Bucket sin 'Public Access Prevention' forzado; riesgo de exposicion publica accidental.",
            savings=0.0,
        )


    @staticmethod
    def uniform_access_disabled_rule(client_id: int):
        return StorageRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('uniform_bucket_level_access') is not True,
            finding_type="BUCKET_UNIFORM_ACCESS_DISABLED",
            severity="MEDIUM",
            message="Bucket sin Uniform Bucket-Level Access habilitado; los permisos por objeto (ACLs) dificultan auditar accesos.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="CloudStorage",
            resource_type="Bucket",
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
                        gcp_service="CloudStorage",
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
