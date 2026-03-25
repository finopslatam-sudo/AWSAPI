from datetime import datetime, timedelta
from src.models.aws_resource_inventory import AWSResourceInventory
from src.aws.finops.rightsizing.shared import (
    LAMBDA_LOW_INVOCATIONS_THRESHOLD,
    resolve_finding,
    upsert_recommendation,
    get_metric_sum,
    get_metric_average,
)
from src.aws.finops.rightsizing.pricing import (
    next_smaller_lambda_memory,
    lambda_monthly_cost,
)


# =====================================================
# LAMBDA RIGHTSIZING — specific memory reduction
# =====================================================

def evaluate_lambda(session, client_id, aws_account_id):

    count = 0

    functions = AWSResourceInventory.query.filter_by(
        client_id=client_id,
        aws_account_id=aws_account_id,
        service_name="Lambda",
        resource_type="Function",
        is_active=True
    ).all()

    finding_type = "LAMBDA_MEMORY_RIGHTSIZING"
    end   = datetime.utcnow()
    start = end - timedelta(days=7)

    for function in functions:
        memory_size = int((function.resource_metadata or {}).get("memory_size") or 0)

        # Functions at or below 128 MB cannot be reduced further
        if memory_size <= 128:
            resolve_finding(client_id, aws_account_id, function.resource_id, finding_type)
            continue

        try:
            cloudwatch = session.client("cloudwatch", region_name=function.region)

            total_invocations = get_metric_sum(
                cloudwatch=cloudwatch,
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions=[{"Name": "FunctionName", "Value": function.resource_id}],
                start=start,
                end=end,
            )

            avg_duration_ms = get_metric_average(
                cloudwatch=cloudwatch,
                namespace="AWS/Lambda",
                metric_name="Duration",
                dimensions=[{"Name": "FunctionName", "Value": function.resource_id}],
                start=start,
                end=end,
            )
        except Exception as e:
            print(f"[LAMBDA RIGHTSIZING ERROR]: {str(e)}")
            continue

        # No invocations in 7 days + high memory → flag as dormant
        if (total_invocations is None or total_invocations == 0) and memory_size > 1024:
            upsert_recommendation(
                client_id=client_id,
                aws_account_id=aws_account_id,
                resource_id=function.resource_id,
                resource_type=function.resource_type,
                region=function.region,
                aws_service="Lambda",
                finding_type=finding_type,
                severity="LOW",
                message=(
                    f"Sin invocaciones en 7 días | "
                    f"Memoria actual: {memory_size} MB → Recomendado: 512 MB. "
                    f"Evaluar si la función sigue siendo necesaria."
                ),
                estimated_monthly_savings=0,
            )
            count += 1
            continue

        if total_invocations is None:
            resolve_finding(client_id, aws_account_id, function.resource_id, finding_type)
            continue

        # Low invocations + oversized memory → recommend specific reduction
        if total_invocations < LAMBDA_LOW_INVOCATIONS_THRESHOLD and memory_size > 1024:
            monthly_inv  = total_invocations * (30 / 7)
            dur_ms       = avg_duration_ms if avg_duration_ms else 500.0
            recommended  = next_smaller_lambda_memory(memory_size) or 512
            current_cost = lambda_monthly_cost(memory_size, int(monthly_inv), dur_ms)
            rec_cost     = lambda_monthly_cost(recommended, int(monthly_inv), dur_ms)
            savings      = round(max(current_cost - rec_cost, 0), 4)

            upsert_recommendation(
                client_id=client_id,
                aws_account_id=aws_account_id,
                resource_id=function.resource_id,
                resource_type=function.resource_type,
                region=function.region,
                aws_service="Lambda",
                finding_type=finding_type,
                severity="LOW",
                message=(
                    f"{int(total_invocations)} invocaciones en 7 días | "
                    f"Memoria: {memory_size} MB → Recomendado: {recommended} MB | "
                    f"Duración promedio: {dur_ms:.0f} ms | "
                    f"Ahorro estimado: ${savings:.4f}/mes"
                ),
                estimated_monthly_savings=savings,
            )
            count += 1
        else:
            resolve_finding(client_id, aws_account_id, function.resource_id, finding_type)

    return count
