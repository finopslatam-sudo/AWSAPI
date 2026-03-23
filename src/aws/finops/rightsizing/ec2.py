from datetime import datetime, timedelta
from src.models.aws_resource_inventory import AWSResourceInventory
from src.aws.finops.rightsizing.shared import (
    EC2_CPU_THRESHOLD,
    resolve_finding,
    upsert_recommendation,
    get_metric_average,
)


# =====================================================
# EC2 RIGHTSIZING
# =====================================================

def evaluate_ec2(session, client_id, aws_account_id):

    count = 0

    instances = AWSResourceInventory.query.filter_by(
        client_id=client_id,
        aws_account_id=aws_account_id,
        service_name="EC2",
        resource_type="Instance",
        is_active=True
    ).all()

    for instance in instances:
        finding_type = "EC2_UNDERUTILIZED"

        if instance.state != "running":
            resolve_finding(
                client_id,
                aws_account_id,
                instance.resource_id,
                finding_type
            )
            continue

        region = instance.region
        instance_id = instance.resource_id

        cloudwatch = session.client(
            "cloudwatch",
            region_name=region
        )

        end = datetime.utcnow()
        start = end - timedelta(days=7)

        try:
            avg_cpu = get_metric_average(
                cloudwatch=cloudwatch,
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                dimensions=[
                    {"Name": "InstanceId", "Value": instance_id}
                ],
                start=start,
                end=end
            )
        except Exception as e:
            print(f"[EC2 RIGHTSIZING ERROR]: {str(e)}")
            continue

        if avg_cpu is None:
            resolve_finding(
                client_id,
                aws_account_id,
                instance_id,
                finding_type
            )
            continue

        if avg_cpu < EC2_CPU_THRESHOLD:
            upsert_recommendation(
                client_id=client_id,
                aws_account_id=instance.aws_account_id,
                resource_id=instance_id,
                resource_type="Instance",
                region=region,
                aws_service="EC2",
                finding_type=finding_type,
                severity="MEDIUM",
                message=f"CPU promedio de los ultimos 7 dias: {round(avg_cpu, 2)}%. La instancia parece sobredimensionada.",
                estimated_monthly_savings=100.0
            )
            count += 1
        else:
            resolve_finding(
                client_id,
                aws_account_id,
                instance_id,
                finding_type
            )

    return count


# =====================================================
# EBS RIGHTSIZING
# =====================================================

def evaluate_ebs(client_id, aws_account_id):

    count = 0

    volumes = AWSResourceInventory.query.filter_by(
        client_id=client_id,
        aws_account_id=aws_account_id,
        service_name="EBS",
        resource_type="Volume",
        is_active=True
    ).all()

    finding_type = "EBS_GP2_TO_GP3"

    for volume in volumes:
        metadata = volume.resource_metadata or {}
        volume_type = metadata.get("volume_type")
        size_gb = float(metadata.get("size_gb") or 0)

        if volume_type == "gp2" and size_gb > 0:
            estimated_savings = round(max(size_gb * 0.02, 1.0), 2)

            upsert_recommendation(
                client_id=client_id,
                aws_account_id=aws_account_id,
                resource_id=volume.resource_id,
                resource_type=volume.resource_type,
                region=volume.region,
                aws_service="EBS",
                finding_type=finding_type,
                severity="MEDIUM",
                message=f"El volumen usa gp2 ({int(size_gb)} GB). Evaluar migracion a gp3 para reducir costo y mantener rendimiento.",
                estimated_monthly_savings=estimated_savings
            )
            count += 1
        else:
            resolve_finding(
                client_id,
                aws_account_id,
                volume.resource_id,
                finding_type
            )

    return count
