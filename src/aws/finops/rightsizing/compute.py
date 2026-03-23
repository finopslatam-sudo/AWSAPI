from datetime import datetime, timedelta
from src.models.aws_resource_inventory import AWSResourceInventory
from src.aws.finops.rightsizing.shared import (
    NAT_LOW_TRAFFIC_BYTES,
    resolve_finding,
    upsert_recommendation,
    get_metric_sum,
)


# =====================================================
# ECS OPTIMIZATION REVIEW
# =====================================================

def evaluate_ecs(client_id, aws_account_id):

    count = 0

    services = AWSResourceInventory.query.filter_by(
        client_id=client_id,
        aws_account_id=aws_account_id,
        service_name="ECS",
        resource_type="Service",
        is_active=True
    ).all()

    finding_type = "ECS_SERVICE_RIGHTSIZING_REVIEW"

    for service in services:
        metadata = service.resource_metadata or {}
        desired_count = int(metadata.get("desired_count") or 0)
        running_count = int(metadata.get("running_count") or 0)
        pending_count = int(metadata.get("pending_count") or 0)

        qualifies = desired_count == 0 or (
            desired_count > 0 and running_count == 0 and pending_count == 0
        )

        if qualifies:
            upsert_recommendation(
                client_id=client_id,
                aws_account_id=aws_account_id,
                resource_id=service.resource_id,
                resource_type=service.resource_type,
                region=service.region,
                aws_service="ECS",
                finding_type=finding_type,
                severity="LOW",
                message=f"El servicio ECS tiene desired={desired_count}, running={running_count}, pending={pending_count}. Conviene revisar su capacidad o necesidad operativa.",
                estimated_monthly_savings=0
            )
            count += 1
        else:
            resolve_finding(
                client_id,
                aws_account_id,
                service.resource_id,
                finding_type
            )

    return count


# =====================================================
# EKS OPTIMIZATION REVIEW
# =====================================================

def evaluate_eks(client_id, aws_account_id):

    count = 0

    nodegroups = AWSResourceInventory.query.filter_by(
        client_id=client_id,
        aws_account_id=aws_account_id,
        service_name="EKS",
        resource_type="NodeGroup",
        is_active=True
    ).all()

    finding_type = "EKS_NODEGROUP_RIGHTSIZING_REVIEW"

    for nodegroup in nodegroups:
        metadata = nodegroup.resource_metadata or {}
        min_size = int(metadata.get("min_size") or 0)
        max_size = int(metadata.get("max_size") or 0)
        desired_size = int(metadata.get("desired_size") or 0)

        qualifies = desired_size == 0 or (
            desired_size > 0 and max_size >= max(desired_size * 3, desired_size + 3)
        )

        if qualifies:
            upsert_recommendation(
                client_id=client_id,
                aws_account_id=aws_account_id,
                resource_id=nodegroup.resource_id,
                resource_type=nodegroup.resource_type,
                region=nodegroup.region,
                aws_service="EKS",
                finding_type=finding_type,
                severity="LOW",
                message=f"El node group tiene min={min_size}, desired={desired_size}, max={max_size}. Conviene revisar su escalado para evitar capacidad ociosa.",
                estimated_monthly_savings=0
            )
            count += 1
        else:
            resolve_finding(
                client_id,
                aws_account_id,
                nodegroup.resource_id,
                finding_type
            )

    return count


# =====================================================
# NAT GATEWAY OPTIMIZATION
# =====================================================

def evaluate_nat(session, client_id, aws_account_id):

    count = 0

    gateways = AWSResourceInventory.query.filter_by(
        client_id=client_id,
        aws_account_id=aws_account_id,
        service_name="NAT",
        resource_type="NatGateway",
        is_active=True
    ).all()

    finding_type = "NAT_IDLE_GATEWAY"
    end = datetime.utcnow()
    start = end - timedelta(days=7)

    for gateway in gateways:
        if gateway.state != "available":
            resolve_finding(
                client_id,
                aws_account_id,
                gateway.resource_id,
                finding_type
            )
            continue

        try:
            cloudwatch = session.client("cloudwatch", region_name=gateway.region)
            bytes_out = get_metric_sum(
                cloudwatch=cloudwatch,
                namespace="AWS/NATGateway",
                metric_name="BytesOutToDestination",
                dimensions=[
                    {"Name": "NatGatewayId", "Value": gateway.resource_id}
                ],
                start=start,
                end=end
            ) or 0
            bytes_in = get_metric_sum(
                cloudwatch=cloudwatch,
                namespace="AWS/NATGateway",
                metric_name="BytesInFromSource",
                dimensions=[
                    {"Name": "NatGatewayId", "Value": gateway.resource_id}
                ],
                start=start,
                end=end
            ) or 0
        except Exception as e:
            print(f"[NAT RIGHTSIZING ERROR]: {str(e)}")
            continue

        total_bytes = bytes_in + bytes_out

        if total_bytes < NAT_LOW_TRAFFIC_BYTES:
            upsert_recommendation(
                client_id=client_id,
                aws_account_id=aws_account_id,
                resource_id=gateway.resource_id,
                resource_type=gateway.resource_type,
                region=gateway.region,
                aws_service="NAT",
                finding_type=finding_type,
                severity="MEDIUM",
                message=f"El NAT Gateway ha procesado solo {(total_bytes / (1024 ** 3)):.2f} GB en 7 dias. Evaluar si sigue siendo necesario o si puede redisenarse la salida.",
                estimated_monthly_savings=32.0
            )
            count += 1
        else:
            resolve_finding(
                client_id,
                aws_account_id,
                gateway.resource_id,
                finding_type
            )

    return count
