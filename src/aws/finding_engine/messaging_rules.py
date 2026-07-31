from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class MessagingRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += MessagingRules.sns_no_subscriptions_rule(client_id)
        total += MessagingRules.sqs_high_retention_rule(client_id)
        return total

    # =====================================================
    # SNS TOPIC SIN SUSCRIPCIONES (HUÉRFANO)
    # =====================================================
    @staticmethod
    def sns_no_subscriptions_rule(client_id: int):

        finding_type = "SNS_TOPIC_NO_SUBSCRIPTIONS"
        severity = "LOW"
        message = "Topic de SNS sin suscripciones activas; probablemente quedó huérfano de una integración anterior."
        savings = 0

        resources = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="SNS",
            resource_type="Topic",
            is_active=True
        ).all()

        return MessagingRules._apply(
            client_id, resources,
            condition=lambda r: (r.resource_metadata or {}).get("subscription_count") == 0,
            finding_type=finding_type, severity=severity, message=message, savings=savings,
            aws_service="SNS",
        )

    # =====================================================
    # SQS CON RETENCIÓN MÁXIMA (14 DÍAS)
    # =====================================================
    @staticmethod
    def sqs_high_retention_rule(client_id: int):

        finding_type = "SQS_MESSAGE_RETENTION_HIGH"
        severity = "LOW"
        message = "Cola SQS configurada con el período máximo de retención (14 días); revisar si es intencional, ya que aumenta el almacenamiento de mensajes no consumidos."
        savings = 0

        resources = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="SQS",
            resource_type="Queue",
            is_active=True
        ).all()

        return MessagingRules._apply(
            client_id, resources,
            condition=lambda r: int((r.resource_metadata or {}).get("message_retention_period") or 0) >= 1209600,
            finding_type=finding_type, severity=severity, message=message, savings=savings,
            aws_service="SQS",
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _apply(client_id, resources, condition, finding_type, severity, message, savings, aws_service):

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
                else:
                    created = AWSFinding.upsert_finding(
                        client_id=client_id,
                        aws_account_id=resource.aws_account_id,
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        region=resource.region,
                        aws_service=aws_service,
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
