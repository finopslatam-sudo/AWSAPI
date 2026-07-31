from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class SageMakerRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += SageMakerRules.endpoint_always_on_rule(client_id)
        total += SageMakerRules.notebook_running_rule(client_id)
        return total

    # =====================================================
    # ENDPOINT DE INFERENCIA SIEMPRE ENCENDIDO
    # =====================================================
    @staticmethod
    def endpoint_always_on_rule(client_id: int):

        return SageMakerRules._evaluate_rule(
            client_id,
            resource_type="Endpoint",
            condition=lambda r: r.state == "InService",
            finding_type="SAGEMAKER_ENDPOINT_ALWAYS_ON",
            severity="MEDIUM",
            message="Endpoint de SageMaker activo 24/7; se factura por hora independiente del tráfico de inferencia. Evaluar Serverless Inference o Auto Scaling si el uso es intermitente.",
            savings=0,
        )

    # =====================================================
    # NOTEBOOK INSTANCE ENCENDIDA
    # =====================================================
    @staticmethod
    def notebook_running_rule(client_id: int):

        return SageMakerRules._evaluate_rule(
            client_id,
            resource_type="NotebookInstance",
            condition=lambda r: r.state == "InService",
            finding_type="NOTEBOOK_INSTANCE_RUNNING",
            severity="HIGH",
            message="Notebook Instance de SageMaker encendida; suele quedar olvidada corriendo fuera de horario de trabajo, generando costo innecesario.",
            savings=15.0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, resource_type, condition, finding_type, severity, message, savings):

        resources = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="SageMaker",
            resource_type=resource_type,
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
                        aws_service="SageMaker",
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
