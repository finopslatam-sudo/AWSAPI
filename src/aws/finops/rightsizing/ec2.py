from datetime import datetime, timedelta
from src.models.aws_resource_inventory import AWSResourceInventory
from src.aws.finops.rightsizing.shared import (
    EC2_CPU_THRESHOLD,
    resolve_finding,
    upsert_recommendation,
    get_metric_average,
)
from src.aws.finops.rightsizing.pricing import EC2_DOWNSIZE, ec2_monthly


# =====================================================
# EC2 RIGHTSIZING — specific instance downsize
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
            resolve_finding(client_id, aws_account_id, instance.resource_id, finding_type)
            continue

        region       = instance.region
        instance_id  = instance.resource_id
        instance_type = (instance.resource_metadata or {}).get("instance_type", "")

        cloudwatch = session.client("cloudwatch", region_name=region)
        end   = datetime.utcnow()
        start = end - timedelta(days=7)

        try:
            avg_cpu = get_metric_average(
                cloudwatch=cloudwatch,
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                start=start,
                end=end,
            )
        except Exception as e:
            print(f"[EC2 RIGHTSIZING ERROR]: {str(e)}")
            continue

        if avg_cpu is None:
            resolve_finding(client_id, aws_account_id, instance_id, finding_type)
            continue

        if avg_cpu < EC2_CPU_THRESHOLD:
            recommended  = EC2_DOWNSIZE.get(instance_type)
            current_mo   = ec2_monthly(instance_type)

            if recommended and current_mo > 0:
                rec_mo   = ec2_monthly(recommended)
                savings  = round(current_mo - rec_mo, 2)
                severity = "HIGH" if savings >= 100 else "MEDIUM"
                message  = (
                    f"CPU promedio 7d: {round(avg_cpu, 1)}% | "
                    f"Actual: {instance_type} (${current_mo:.0f}/mes) → "
                    f"Recomendado: {recommended} (${rec_mo:.0f}/mes) | "
                    f"Ahorro: ${savings:.0f}/mes"
                )
            else:
                savings  = round(max(current_mo * 0.5, 10.0), 2) if current_mo > 0 else 50.0
                severity = "MEDIUM"
                message  = (
                    f"CPU promedio 7d: {round(avg_cpu, 1)}% | "
                    f"Instancia {instance_type} subutilizada. "
                    f"Evaluar downsize o apagado."
                )

            upsert_recommendation(
                client_id=client_id,
                aws_account_id=instance.aws_account_id,
                resource_id=instance_id,
                resource_type="Instance",
                region=region,
                aws_service="EC2",
                finding_type=finding_type,
                severity=severity,
                message=message,
                estimated_monthly_savings=savings,
            )
            count += 1
        else:
            resolve_finding(client_id, aws_account_id, instance_id, finding_type)

    return count


# =====================================================
# EBS RIGHTSIZING — gp2 → gp3 with real savings
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
        metadata    = volume.resource_metadata or {}
        volume_type = metadata.get("volume_type")
        size_gb     = float(metadata.get("size_gb") or 0)

        if volume_type == "gp2" and size_gb > 0:
            # gp2: $0.10/GB-month  |  gp3: $0.08/GB-month (includes 3000 IOPS + 125 MB/s free)
            current_cost = round(size_gb * 0.10, 2)
            rec_cost     = round(size_gb * 0.08, 2)
            savings      = round(size_gb * 0.02, 2)

            upsert_recommendation(
                client_id=client_id,
                aws_account_id=aws_account_id,
                resource_id=volume.resource_id,
                resource_type=volume.resource_type,
                region=volume.region,
                aws_service="EBS",
                finding_type=finding_type,
                severity="MEDIUM",
                message=(
                    f"Volumen gp2 de {int(size_gb)} GB | "
                    f"Actual: gp2 (${current_cost:.0f}/mes) → "
                    f"Recomendado: gp3 (${rec_cost:.0f}/mes) | "
                    f"Ahorro: ${savings:.0f}/mes "
                    f"(gp3 incluye 3000 IOPS + 125 MB/s gratis)"
                ),
                estimated_monthly_savings=savings,
            )
            count += 1
        else:
            resolve_finding(client_id, aws_account_id, volume.resource_id, finding_type)

    return count
