from datetime import datetime, timedelta
from src.models.aws_resource_inventory import AWSResourceInventory
from src.aws.finops.rightsizing.shared import (
    CLOUDWATCH_MIN_STORED_BYTES,
    S3_MIN_BUCKET_SIZE_BYTES,
    S3_MIN_BUCKET_AGE_DAYS,
    resolve_finding,
    upsert_recommendation,
    get_metric_average,
    get_metric_sum,
)
from src.aws.finops.rightsizing.pricing import (
    DYNAMO_WCU_MONTH,
    DYNAMO_RCU_MONTH,
)


# =====================================================
# DYNAMODB — compare provisioned vs consumed WCU/RCU
# =====================================================

def evaluate_dynamodb(session, client_id, aws_account_id):

    count = 0

    tables = AWSResourceInventory.query.filter_by(
        client_id=client_id,
        aws_account_id=aws_account_id,
        service_name="DynamoDB",
        resource_type="Table",
        is_active=True
    ).all()

    finding_type = "DYNAMODB_PROVISIONED_RIGHTSIZING"
    end   = datetime.utcnow()
    start = end - timedelta(days=7)

    for table in tables:
        metadata     = table.resource_metadata or {}
        billing_mode = metadata.get("billing_mode")

        if billing_mode != "PROVISIONED":
            resolve_finding(client_id, aws_account_id, table.resource_id, finding_type)
            continue

        prov_wcu = int(metadata.get("provisioned_wcu") or 0)
        prov_rcu = int(metadata.get("provisioned_rcu") or 0)

        # Try to get consumed capacity from CloudWatch
        consumed_wcu = consumed_rcu = None
        try:
            cw = session.client("cloudwatch", region_name=table.region)
            dims = [{"Name": "TableName", "Value": table.resource_id}]

            raw_wcu = get_metric_sum(
                cloudwatch=cw, namespace="AWS/DynamoDB",
                metric_name="ConsumedWriteCapacityUnits",
                dimensions=dims, start=start, end=end,
            )
            raw_rcu = get_metric_sum(
                cloudwatch=cw, namespace="AWS/DynamoDB",
                metric_name="ConsumedReadCapacityUnits",
                dimensions=dims, start=start, end=end,
            )
            # Convert 7-day sum (units) to avg daily, then estimate provisioned-equivalent
            if raw_wcu is not None:
                consumed_wcu = int(raw_wcu / (7 * 86400))   # avg units/second → equiv WCU
            if raw_rcu is not None:
                consumed_rcu = int(raw_rcu / (7 * 86400))
        except Exception as e:
            print(f"[DYNAMODB RIGHTSIZING ERROR]: {str(e)}")

        if consumed_wcu is not None and consumed_rcu is not None and prov_wcu > 0:
            # Only flag if consumed is less than 50% of provisioned
            if consumed_wcu < prov_wcu * 0.5 or consumed_rcu < prov_rcu * 0.5:
                rec_wcu    = max(int(consumed_wcu * 1.5), 1)
                rec_rcu    = max(int(consumed_rcu * 1.5), 1)
                cur_cost   = round(prov_wcu * DYNAMO_WCU_MONTH + prov_rcu * DYNAMO_RCU_MONTH, 2)
                rec_cost   = round(rec_wcu * DYNAMO_WCU_MONTH + rec_rcu * DYNAMO_RCU_MONTH, 2)
                savings    = round(max(cur_cost - rec_cost, 0), 2)

                upsert_recommendation(
                    client_id=client_id, aws_account_id=aws_account_id,
                    resource_id=table.resource_id, resource_type=table.resource_type,
                    region=table.region, aws_service="DynamoDB",
                    finding_type=finding_type, severity="LOW",
                    message=(
                        f"Modo PROVISIONED | "
                        f"Actual: {prov_wcu} WCU / {prov_rcu} RCU (${cur_cost:.2f}/mes) | "
                        f"Consumido promedio: ~{consumed_wcu} WCU / ~{consumed_rcu} RCU | "
                        f"Recomendado: {rec_wcu} WCU / {rec_rcu} RCU (${rec_cost:.2f}/mes) | "
                        f"Ahorro: ${savings:.2f}/mes. O cambiar a On-Demand."
                    ),
                    estimated_monthly_savings=savings,
                )
                count += 1
                continue

        # Fallback: no CloudWatch data or well-utilized — generic message
        if billing_mode == "PROVISIONED" and prov_wcu == 0:
            upsert_recommendation(
                client_id=client_id, aws_account_id=aws_account_id,
                resource_id=table.resource_id, resource_type=table.resource_type,
                region=table.region, aws_service="DynamoDB",
                finding_type=finding_type, severity="LOW",
                message="Tabla en modo PROVISIONED. Revisar si On-Demand resulta más económico.",
                estimated_monthly_savings=0,
            )
            count += 1
        else:
            resolve_finding(client_id, aws_account_id, table.resource_id, finding_type)

    return count


# =====================================================
# CLOUDWATCH LOGS — retention policy recommendation
# =====================================================

def evaluate_cloudwatch(client_id, aws_account_id):

    count = 0

    log_groups = AWSResourceInventory.query.filter_by(
        client_id=client_id,
        aws_account_id=aws_account_id,
        service_name="CloudWatch",
        resource_type="LogGroup",
        is_active=True
    ).all()

    finding_type = "CLOUDWATCH_STORAGE_RIGHTSIZING"

    for lg in log_groups:
        metadata       = lg.resource_metadata or {}
        stored_bytes   = int(metadata.get("stored_bytes") or 0)
        retention_days = metadata.get("retention_days")

        qualifies = (
            stored_bytes >= CLOUDWATCH_MIN_STORED_BYTES
            and (retention_days is None or retention_days > 90)
        )

        if qualifies:
            stored_gb    = stored_bytes / (1024 ** 3)
            current_cost = round(stored_gb * 0.03, 2)
            # Estimate: setting 90-day retention ≈ storing ~30% of current data
            rec_cost     = round(current_cost * 0.3, 2)
            savings      = round(current_cost - rec_cost, 2)
            ret_label    = (
                "sin retención definida"
                if retention_days is None
                else f"retención: {retention_days} días"
            )

            upsert_recommendation(
                client_id=client_id, aws_account_id=aws_account_id,
                resource_id=lg.resource_id, resource_type=lg.resource_type,
                region=lg.region, aws_service="CloudWatch",
                finding_type=finding_type, severity="LOW",
                message=(
                    f"Log group almacena {stored_gb:.2f} GB ({ret_label}) | "
                    f"Costo actual: ${current_cost:.2f}/mes | "
                    f"Reducir retención a 90 días → ${rec_cost:.2f}/mes | "
                    f"Ahorro estimado: ${savings:.2f}/mes"
                ),
                estimated_monthly_savings=savings,
            )
            count += 1
        else:
            resolve_finding(client_id, aws_account_id, lg.resource_id, finding_type)

    return count


# =====================================================
# S3 — Intelligent-Tiering recommendation
# =====================================================

def evaluate_s3(session, client_id, aws_account_id):

    count = 0

    buckets = AWSResourceInventory.query.filter_by(
        client_id=client_id,
        aws_account_id=aws_account_id,
        service_name="S3",
        resource_type="Bucket",
        is_active=True
    ).all()

    finding_type = "S3_STORAGE_RIGHTSIZING_REVIEW"
    end   = datetime.utcnow()
    start = end - timedelta(days=7)

    for bucket in buckets:
        created_at = (bucket.resource_metadata or {}).get("creation_date")
        try:
            created_dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        except Exception:
            created_dt = None

        bucket_age_days = (
            (end - created_dt.replace(tzinfo=None)).days if created_dt else 0
        )

        try:
            cw = session.client("cloudwatch", region_name="us-east-1")
            bucket_size = get_metric_average(
                cloudwatch=cw, namespace="AWS/S3",
                metric_name="BucketSizeBytes",
                dimensions=[
                    {"Name": "BucketName",   "Value": bucket.resource_id},
                    {"Name": "StorageType",  "Value": "StandardStorage"},
                ],
                start=start, end=end,
            )
        except Exception as e:
            print(f"[S3 RIGHTSIZING ERROR]: {str(e)}")
            bucket_size = None

        qualifies = (
            bucket_size is not None
            and bucket_size >= S3_MIN_BUCKET_SIZE_BYTES
            and bucket_age_days >= S3_MIN_BUCKET_AGE_DAYS
        )

        if qualifies and bucket_size is not None:
            size_gb      = bucket_size / (1024 ** 3)
            # Standard: $0.023/GB | Intelligent-Tiering infrequent tier: ~$0.0125/GB
            current_cost = round(size_gb * 0.023, 2)
            rec_cost     = round(size_gb * 0.0125, 2)
            savings      = round(current_cost - rec_cost, 2)

            upsert_recommendation(
                client_id=client_id, aws_account_id=aws_account_id,
                resource_id=bucket.resource_id, resource_type=bucket.resource_type,
                region=bucket.region, aws_service="S3",
                finding_type=finding_type, severity="LOW",
                message=(
                    f"Bucket de {size_gb:.2f} GB con {bucket_age_days} días de antigüedad | "
                    f"Standard: ${current_cost:.2f}/mes → "
                    f"Intelligent-Tiering (acceso infrecuente): ${rec_cost:.2f}/mes | "
                    f"Ahorro estimado: ${savings:.2f}/mes. "
                    f"Revisar también lifecycle para mover objetos >90 días a S3-IA o Glacier."
                ),
                estimated_monthly_savings=savings,
            )
            count += 1
        else:
            resolve_finding(client_id, aws_account_id, bucket.resource_id, finding_type)

    return count
