from datetime import datetime, timedelta
from src.models.aws_resource_inventory import AWSResourceInventory
from src.aws.finops.rightsizing.shared import (
    RDS_CPU_THRESHOLD,
    REDSHIFT_CPU_THRESHOLD,
    resolve_finding,
    upsert_recommendation,
    get_metric_average,
)


# =====================================================
# RDS RIGHTSIZING
# =====================================================

def evaluate_rds(session, client_id, aws_account_id):

    count = 0

    rds_instances = AWSResourceInventory.query.filter_by(
        client_id=client_id,
        aws_account_id=aws_account_id,
        service_name="RDS",
        resource_type="DBInstance",
        is_active=True
    ).all()

    for db_instance in rds_instances:
        finding_type = "RDS_UNDERUTILIZED"

        if db_instance.state != "available":
            resolve_finding(
                client_id,
                aws_account_id,
                db_instance.resource_id,
                finding_type
            )
            continue

        region = db_instance.region
        db_identifier = db_instance.resource_id

        cloudwatch = session.client(
            "cloudwatch",
            region_name=region
        )

        end = datetime.utcnow()
        start = end - timedelta(days=7)

        try:
            avg_cpu = get_metric_average(
                cloudwatch=cloudwatch,
                namespace="AWS/RDS",
                metric_name="CPUUtilization",
                dimensions=[
                    {"Name": "DBInstanceIdentifier", "Value": db_identifier}
                ],
                start=start,
                end=end
            )
        except Exception as e:
            print(f"[RDS RIGHTSIZING ERROR]: {str(e)}")
            continue

        if avg_cpu is None:
            resolve_finding(
                client_id,
                aws_account_id,
                db_identifier,
                finding_type
            )
            continue

        if avg_cpu < RDS_CPU_THRESHOLD:
            upsert_recommendation(
                client_id=client_id,
                aws_account_id=db_instance.aws_account_id,
                resource_id=db_identifier,
                resource_type="DBInstance",
                region=region,
                aws_service="RDS",
                finding_type=finding_type,
                severity="MEDIUM",
                message=f"CPU promedio de los ultimos 7 dias: {round(avg_cpu, 2)}%. La instancia RDS parece sobredimensionada.",
                estimated_monthly_savings=50.0
            )
            count += 1
        else:
            resolve_finding(
                client_id,
                aws_account_id,
                db_identifier,
                finding_type
            )

    return count


# =====================================================
# REDSHIFT RIGHTSIZING
# =====================================================

def evaluate_redshift(session, client_id, aws_account_id):

    count = 0

    clusters = AWSResourceInventory.query.filter_by(
        client_id=client_id,
        aws_account_id=aws_account_id,
        service_name="Redshift",
        resource_type="Cluster",
        is_active=True
    ).all()

    finding_type = "REDSHIFT_UNDERUTILIZED"
    end = datetime.utcnow()
    start = end - timedelta(days=7)

    for cluster in clusters:
        if cluster.state != "available":
            resolve_finding(
                client_id,
                aws_account_id,
                cluster.resource_id,
                finding_type
            )
            continue

        try:
            cloudwatch = session.client("cloudwatch", region_name=cluster.region)
            avg_cpu = get_metric_average(
                cloudwatch=cloudwatch,
                namespace="AWS/Redshift",
                metric_name="CPUUtilization",
                dimensions=[
                    {"Name": "ClusterIdentifier", "Value": cluster.resource_id}
                ],
                start=start,
                end=end
            )
        except Exception as e:
            print(f"[REDSHIFT RIGHTSIZING ERROR]: {str(e)}")
            continue

        if avg_cpu is not None and avg_cpu < REDSHIFT_CPU_THRESHOLD:
            node_count = (cluster.resource_metadata or {}).get("number_of_nodes") or 1
            estimated_savings = round(max(float(node_count) * 30.0, 30.0), 2)
            upsert_recommendation(
                client_id=client_id,
                aws_account_id=aws_account_id,
                resource_id=cluster.resource_id,
                resource_type=cluster.resource_type,
                region=cluster.region,
                aws_service="Redshift",
                finding_type=finding_type,
                severity="MEDIUM",
                message=f"CPU promedio de los ultimos 7 dias: {round(avg_cpu, 2)}%. El cluster parece sobredimensionado.",
                estimated_monthly_savings=estimated_savings
            )
            count += 1
        else:
            resolve_finding(
                client_id,
                aws_account_id,
                cluster.resource_id,
                finding_type
            )

    return count
