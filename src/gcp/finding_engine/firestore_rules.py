from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class FirestoreRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += FirestoreRules.delete_protection_disabled_rule(client_id)
        total += FirestoreRules.datastore_mode_review_rule(client_id)
        return total

    @staticmethod
    def delete_protection_disabled_rule(client_id: int):
        return FirestoreRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('delete_protection_state') != 'DELETE_PROTECTION_ENABLED',
            finding_type="FIRESTORE_DELETE_PROTECTION_DISABLED",
            severity="MEDIUM",
            message="Base de datos Firestore sin proteccion contra borrado habilitada; riesgo de eliminacion accidental.",
            savings=0.0,
        )


    @staticmethod
    def datastore_mode_review_rule(client_id: int):
        return FirestoreRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('type') == 'DATASTORE_MODE',
            finding_type="FIRESTORE_DATASTORE_MODE_REVIEW",
            severity="LOW",
            message="Base de datos Firestore en modo Datastore (legacy); evaluar migrar a modo Native para nuevas funcionalidades.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="Firestore",
            resource_type="Database",
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
                        gcp_service="Firestore",
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
