from datetime import datetime
from src.models.aws_finding import AWSFinding


# =====================================================
# THRESHOLDS / CONSTANTS
# =====================================================

EC2_CPU_THRESHOLD = 10.0
RDS_CPU_THRESHOLD = 10.0
REDSHIFT_CPU_THRESHOLD = 10.0
LAMBDA_LOW_INVOCATIONS_THRESHOLD = 100
NAT_LOW_TRAFFIC_BYTES = 1_000_000_000
CLOUDWATCH_MIN_STORED_BYTES = 1_000_000_000
S3_MIN_BUCKET_SIZE_BYTES = 10 * 1024 * 1024 * 1024
S3_MIN_BUCKET_AGE_DAYS = 90


# =====================================================
# SHARED HELPERS
# =====================================================

def resolve_finding(client_id, aws_account_id, resource_id, finding_type):
    existing = (
        AWSFinding.query
        .filter_by(
            client_id=client_id,
            aws_account_id=aws_account_id,
            resource_id=resource_id,
            finding_type=finding_type,
            resolved=False
        )
        .all()
    )

    for finding in existing:
        finding.resolved = True
        finding.resolved_at = datetime.utcnow()


def upsert_recommendation(
    client_id,
    aws_account_id,
    resource_id,
    resource_type,
    region,
    aws_service,
    finding_type,
    severity,
    message,
    estimated_monthly_savings
):
    AWSFinding.upsert_finding(
        client_id=client_id,
        aws_account_id=aws_account_id,
        resource_id=resource_id,
        resource_type=resource_type,
        region=region,
        aws_service=aws_service,
        finding_type=finding_type,
        severity=severity,
        message=message,
        estimated_monthly_savings=estimated_monthly_savings
    )


def get_metric_sum(
    cloudwatch,
    namespace,
    metric_name,
    dimensions,
    start,
    end,
    period=86400
):
    metrics = cloudwatch.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=dimensions,
        StartTime=start,
        EndTime=end,
        Period=period,
        Statistics=["Sum"]
    )

    datapoints = metrics.get("Datapoints", [])
    if not datapoints:
        return None

    return sum(d.get("Sum", 0) for d in datapoints)


def get_metric_average(
    cloudwatch,
    namespace,
    metric_name,
    dimensions,
    start,
    end,
    period=86400
):
    metrics = cloudwatch.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=dimensions,
        StartTime=start,
        EndTime=end,
        Period=period,
        Statistics=["Average"]
    )

    datapoints = metrics.get("Datapoints", [])
    if not datapoints:
        return None

    return sum(d.get("Average", 0) for d in datapoints) / len(datapoints)
