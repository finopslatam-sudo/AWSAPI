from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class CloudFrontRules:

    @staticmethod
    def run_all(client_id: int):
        return CloudFrontRules.price_class_all_rule(client_id)

    # =====================================================
    # DISTRIBUCIÓN CON PRICE CLASS "ALL" (LA MÁS COSTOSA)
    # =====================================================
    @staticmethod
    def price_class_all_rule(client_id: int):

        finding_type = "CLOUDFRONT_PRICE_CLASS_ALL"
        severity = "LOW"
        message = "Distribución CloudFront usando Price Class 'All' (todas las edge locations); si el tráfico es regional, una Price Class más acotada reduce el costo por transferencia de datos."
        savings = 0

        resources = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="CloudFront",
            resource_type="Distribution",
            is_active=True
        ).all()

        findings_created = 0

        for resource in resources:
            metadata = resource.resource_metadata or {}
            is_all_edge = metadata.get("price_class") == "PriceClass_All"

            existing = AWSFinding.query.filter_by(
                client_id=client_id,
                resource_id=resource.resource_id,
                finding_type=finding_type
            ).first()

            if is_all_edge:
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
                        aws_service="CloudFront",
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
