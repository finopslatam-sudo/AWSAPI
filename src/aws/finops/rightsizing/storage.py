from datetime import datetime, timedelta
from src.models.aws_resource_inventory import AWSResourceInventory
from src.aws.finops.rightsizing.shared import (
    CLOUDWATCH_MIN_STORED_BYTES,
    S3_MIN_BUCKET_SIZE_BYTES,
    S3_MIN_BUCKET_AGE_DAYS,
    resolve_finding,
    upsert_recommendation,
    get_metric_average,
)


# =====================================================
# DYNAMODB RIGHTSIZING
# =====================================================

def evaluate_dynamodb(client_id, aws_account_id):

    count = 0

    tables = AWSResourceInventory.query.filter_by(
        client_id=client_id,
        aws_account_id=aws_account_id,
        service_name="DynamoDB",
        resource_type="Table",
        is_active=True
    ).all()

    finding_type = "DYNAMODB_PROVISIONED_RIGHTSIZING"

    for table in tables:
        metadata = table.resource_metadata or {}
        billing_mode = metadata.get("billing_mode")

        if billing_mode == "PROVISIONED":
            upsert_recommendation(
                client_id=client_id,
                aws_account_id=aws_account_id,
                resource_id=table.resource_id,
                resource_type=table.resource_type,
                region=table.region,
                aws_service="DynamoDB",
                finding_type=finding_type,
                severity="LOW",
                message="La tabla usa modo PROVISIONED. Revisar si On-Demand o menores capacidades aprovisionadas son suficientes.",
                estimated_monthly_savings=0
            )
            count += 1
        else:
            resolve_finding(
                client_id,
                aws_account_id,
                table.resource_id,
                finding_type
            )

    return count


# =====================================================
# CLOUDWATCH STORAGE OPTIMIZATION
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

    for log_group in log_groups:
        metadata = log_group.resource_metadata or {}
        stored_bytes = int(metadata.get("stored_bytes") or 0)
        retention_days = metadata.get("retention_days")

        qualifies = (
            stored_bytes >= CLOUDWATCH_MIN_STORED_BYTES and
            (retention_days is None or retention_days > 90)
        )

        if qualifies:
            stored_gb = float(stored_bytes) / (1024 ** 3)
            estimated_savings = round(min(max(stored_gb * 0.03, 1.0), 20.0), 2)
            retention_label = (
                "sin retencion definida"
                if retention_days is None
                else f"con retencion de {retention_days} dias"
            )

            upsert_recommendation(
                client_id=client_id,
                aws_account_id=aws_account_id,
                resource_id=log_group.resource_id,
                resource_type=log_group.resource_type,
                region=log_group.region,
                aws_service="CloudWatch",
                finding_type=finding_type,
                severity="LOW",
                message=f"El log group almacena {stored_gb:.2f} GB y esta {retention_label}. Ajustar retencion puede reducir costo.",
                estimated_monthly_savings=estimated_savings
            )
            count += 1
        else:
            resolve_finding(
                client_id,
                aws_account_id,
                log_group.resource_id,
                finding_type
            )

    return count


# =====================================================
# S3 OPTIMIZATION REVIEW
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
    end = datetime.utcnow()
    start = end - timedelta(days=7)

    for bucket in buckets:
        created_at = (bucket.resource_metadata or {}).get("creation_date")
        try:
            created_dt = datetime.fromisoformat(
                str(created_at).replace("Z", "+00:00")
            )
        except Exception:
            created_dt = None

        bucket_age_days = (
            (end - created_dt.replace(tzinfo=None)).days
            if created_dt is not None else 0
        )

        try:
            cloudwatch = session.client("cloudwatch", region_name="us-east-1")
            bucket_size = get_metric_average(
                cloudwatch=cloudwatch,
                namespace="AWS/S3",
                metric_name="BucketSizeBytes",
                dimensions=[
                    {"Name": "BucketName", "Value": bucket.resource_id},
                    {"Name": "StorageType", "Value": "StandardStorage"}
                ],
                start=start,
                end=end
            )
        except Exception as e:
            print(f"[S3 RIGHTSIZING ERROR]: {str(e)}")
            bucket_size = None

        qualifies = (
            bucket_size is not None and
            bucket_size >= S3_MIN_BUCKET_SIZE_BYTES and
            bucket_age_days >= S3_MIN_BUCKET_AGE_DAYS
        )

        if qualifies and bucket_size is not None:
            size_gb = bucket_size / (1024 ** 3)
            upsert_recommendation(
                client_id=client_id,
                aws_account_id=aws_account_id,
                resource_id=bucket.resource_id,
                resource_type=bucket.resource_type,
                region=bucket.region,
                aws_service="S3",
                finding_type=finding_type,
                severity="LOW",
                message=f"El bucket almacena aproximadamente {size_gb:.2f} GB y tiene mas de {bucket_age_days} dias. Conviene revisar lifecycle o Intelligent-Tiering.",
                estimated_monthly_savings=0
            )
            count += 1
        else:
            resolve_finding(
                client_id,
                aws_account_id,
                bucket.resource_id,
                finding_type
            )

    return count
