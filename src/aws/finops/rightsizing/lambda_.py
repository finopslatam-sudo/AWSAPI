from datetime import datetime, timedelta
from src.models.aws_resource_inventory import AWSResourceInventory
from src.aws.finops.rightsizing.shared import (
    LAMBDA_LOW_INVOCATIONS_THRESHOLD,
    resolve_finding,
    upsert_recommendation,
    get_metric_sum,
)


# =====================================================
# LAMBDA RIGHTSIZING
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
    end = datetime.utcnow()
    start = end - timedelta(days=7)

    for function in functions:
        memory_size = int((function.resource_metadata or {}).get("memory_size") or 0)

        if memory_size <= 1024:
            resolve_finding(
                client_id,
                aws_account_id,
                function.resource_id,
                finding_type
            )
            continue

        try:
            cloudwatch = session.client("cloudwatch", region_name=function.region)
            total_invocations = get_metric_sum(
                cloudwatch=cloudwatch,
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions=[
                    {"Name": "FunctionName", "Value": function.resource_id}
                ],
                start=start,
                end=end
            )
        except Exception as e:
            print(f"[LAMBDA RIGHTSIZING ERROR]: {str(e)}")
            continue

        if total_invocations is not None and total_invocations < LAMBDA_LOW_INVOCATIONS_THRESHOLD:
            estimated_savings = round(max((memory_size - 1024) / 1024 * 3, 0), 2)
            upsert_recommendation(
                client_id=client_id,
                aws_account_id=aws_account_id,
                resource_id=function.resource_id,
                resource_type=function.resource_type,
                region=function.region,
                aws_service="Lambda",
                finding_type=finding_type,
                severity="LOW",
                message=f"La funcion tiene {memory_size} MB asignados y solo {int(total_invocations)} invocaciones en 7 dias. Conviene revisar su memoria.",
                estimated_monthly_savings=estimated_savings
            )
            count += 1
        else:
            resolve_finding(
                client_id,
                aws_account_id,
                function.resource_id,
                finding_type
            )

    return count
