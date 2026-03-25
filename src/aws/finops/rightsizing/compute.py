from datetime import datetime, timedelta
from src.models.aws_resource_inventory import AWSResourceInventory
from src.aws.finops.rightsizing.shared import (
    NAT_LOW_TRAFFIC_BYTES,
    resolve_finding,
    upsert_recommendation,
    get_metric_sum,
    get_metric_average,
)
from src.aws.finops.rightsizing.pricing import (
    ECS_CPU_DOWNSIZE, ECS_MIN_MEMORY, ecs_task_monthly, HOURS_MONTH,
)

NAT_FIXED_HR  = 0.045   # per NAT gateway per hour
NAT_DATA_GB   = 0.045   # per GB processed


# =====================================================
# ECS FARGATE RIGHTSIZING — task def CPU/memory + CW
# =====================================================

def evaluate_ecs(session, client_id, aws_account_id):

    count = 0

    services = AWSResourceInventory.query.filter_by(
        client_id=client_id,
        aws_account_id=aws_account_id,
        service_name="ECS",
        resource_type="Service",
        is_active=True
    ).all()

    ft_idle    = "ECS_SERVICE_RIGHTSIZING_REVIEW"
    ft_fargate = "ECS_FARGATE_RIGHTSIZING"

    for service in services:
        metadata      = service.resource_metadata or {}
        desired       = int(metadata.get("desired_count") or 0)
        running       = int(metadata.get("running_count") or 0)
        launch_type   = metadata.get("launch_type", "")
        task_def_arn  = metadata.get("task_definition")
        cluster_arn   = metadata.get("cluster_arn")

        # ── Case 1: idle service (0 tasks) ──────────────────
        if desired == 0 or (desired > 0 and running == 0):
            upsert_recommendation(
                client_id=client_id, aws_account_id=aws_account_id,
                resource_id=service.resource_id, resource_type=service.resource_type,
                region=service.region, aws_service="ECS",
                finding_type=ft_idle, severity="LOW",
                message=(
                    f"Servicio ECS con desired={desired}, running={running}. "
                    f"Sin tareas activas: evaluar necesidad o eliminar."
                ),
                estimated_monthly_savings=0,
            )
            resolve_finding(client_id, aws_account_id, service.resource_id, ft_fargate)
            count += 1
            continue

        # ── Case 2: Fargate + task def available → real check ──
        if launch_type == "FARGATE" and task_def_arn and cluster_arn:
            resolve_finding(client_id, aws_account_id, service.resource_id, ft_idle)

            try:
                ecs_client = session.client("ecs", region_name=service.region)
                task_def   = ecs_client.describe_task_definition(
                    taskDefinition=task_def_arn
                )["taskDefinition"]
                cpu_units  = int(task_def.get("cpu") or 0)
                memory_mb  = int(task_def.get("memory") or 0)
            except Exception as e:
                print(f"[ECS task_def ERROR]: {str(e)}")
                resolve_finding(client_id, aws_account_id, service.resource_id, ft_fargate)
                continue

            if not cpu_units or not memory_mb:
                resolve_finding(client_id, aws_account_id, service.resource_id, ft_fargate)
                continue

            try:
                cluster_name = cluster_arn.split("/")[-1]
                cw  = session.client("cloudwatch", region_name=service.region)
                end = datetime.utcnow()
                st  = end - timedelta(days=7)

                avg_cpu_util = get_metric_average(
                    cloudwatch=cw,
                    namespace="AWS/ECS",
                    metric_name="CPUUtilization",
                    dimensions=[
                        {"Name": "ClusterName", "Value": cluster_name},
                        {"Name": "ServiceName", "Value": service.resource_id},
                    ],
                    start=st, end=end,
                )
            except Exception as e:
                print(f"[ECS CloudWatch ERROR]: {str(e)}")
                resolve_finding(client_id, aws_account_id, service.resource_id, ft_fargate)
                continue

            if avg_cpu_util is None or avg_cpu_util >= 20:
                resolve_finding(client_id, aws_account_id, service.resource_id, ft_fargate)
                continue

            rec_cpu = ECS_CPU_DOWNSIZE.get(cpu_units)
            if not rec_cpu:
                resolve_finding(client_id, aws_account_id, service.resource_id, ft_fargate)
                continue

            rec_mem    = ECS_MIN_MEMORY.get(rec_cpu, memory_mb // 2)
            current_mo = ecs_task_monthly(cpu_units, memory_mb, running)
            rec_mo     = ecs_task_monthly(rec_cpu, rec_mem, running)
            savings    = round(max(current_mo - rec_mo, 0), 2)
            cur_vcpu   = cpu_units / 1024
            rec_vcpu   = rec_cpu / 1024

            upsert_recommendation(
                client_id=client_id, aws_account_id=aws_account_id,
                resource_id=service.resource_id, resource_type=service.resource_type,
                region=service.region, aws_service="ECS",
                finding_type=ft_fargate,
                severity="MEDIUM" if savings > 50 else "LOW",
                message=(
                    f"CPU promedio 7d: {round(avg_cpu_util, 1)}% | "
                    f"Tareas: {running} | "
                    f"Actual: {cur_vcpu}vCPU/{memory_mb}MB (${current_mo:.0f}/mes) → "
                    f"Recomendado: {rec_vcpu}vCPU/{rec_mem}MB (${rec_mo:.0f}/mes) | "
                    f"Ahorro: ${savings:.0f}/mes"
                ),
                estimated_monthly_savings=savings,
            )
            count += 1
        else:
            resolve_finding(client_id, aws_account_id, service.resource_id, ft_idle)
            resolve_finding(client_id, aws_account_id, service.resource_id, ft_fargate)

    return count


# =====================================================
# EKS NODEGROUP — scaling gap review
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

    for ng in nodegroups:
        metadata     = ng.resource_metadata or {}
        min_size     = int(metadata.get("min_size") or 0)
        max_size     = int(metadata.get("max_size") or 0)
        desired_size = int(metadata.get("desired_size") or 0)
        inst_types   = metadata.get("instance_types") or []
        inst_label   = ", ".join(inst_types) if inst_types else "desconocido"

        qualifies = desired_size == 0 or (
            desired_size > 0 and max_size >= max(desired_size * 3, desired_size + 3)
        )

        if qualifies:
            ratio = f"{max_size // desired_size}x" if desired_size > 0 else "N/A"
            upsert_recommendation(
                client_id=client_id, aws_account_id=aws_account_id,
                resource_id=ng.resource_id, resource_type=ng.resource_type,
                region=ng.region, aws_service="EKS",
                finding_type=finding_type, severity="LOW",
                message=(
                    f"NodeGroup ({inst_label}) | "
                    f"min={min_size}, desired={desired_size}, max={max_size} ({ratio} el desired) | "
                    f"Reducir max_size para evitar capacidad ociosa en picos."
                ),
                estimated_monthly_savings=0,
            )
            count += 1
        else:
            resolve_finding(client_id, aws_account_id, ng.resource_id, finding_type)

    return count


# =====================================================
# NAT GATEWAY — low traffic with cost breakdown
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
    end   = datetime.utcnow()
    start = end - timedelta(days=7)

    for gw in gateways:
        if gw.state != "available":
            resolve_finding(client_id, aws_account_id, gw.resource_id, finding_type)
            continue

        try:
            cw = session.client("cloudwatch", region_name=gw.region)
            bytes_out = get_metric_sum(
                cloudwatch=cw, namespace="AWS/NATGateway",
                metric_name="BytesOutToDestination",
                dimensions=[{"Name": "NatGatewayId", "Value": gw.resource_id}],
                start=start, end=end,
            ) or 0
            bytes_in = get_metric_sum(
                cloudwatch=cw, namespace="AWS/NATGateway",
                metric_name="BytesInFromSource",
                dimensions=[{"Name": "NatGatewayId", "Value": gw.resource_id}],
                start=start, end=end,
            ) or 0
        except Exception as e:
            print(f"[NAT RIGHTSIZING ERROR]: {str(e)}")
            continue

        total_bytes = bytes_in + bytes_out

        if total_bytes < NAT_LOW_TRAFFIC_BYTES:
            week_gb     = total_bytes / (1024 ** 3)
            monthly_gb  = week_gb * (30 / 7)
            fixed_mo    = round(NAT_FIXED_HR * HOURS_MONTH, 2)
            data_mo     = round(monthly_gb * NAT_DATA_GB, 2)
            total_mo    = round(fixed_mo + data_mo, 2)

            upsert_recommendation(
                client_id=client_id, aws_account_id=aws_account_id,
                resource_id=gw.resource_id, resource_type=gw.resource_type,
                region=gw.region, aws_service="NAT",
                finding_type=finding_type, severity="MEDIUM",
                message=(
                    f"Tráfico 7d: {week_gb:.2f} GB (~{monthly_gb:.0f} GB/mes) | "
                    f"Costo fijo: ${fixed_mo:.0f}/mes + Datos: ${data_mo:.0f}/mes = ${total_mo:.0f}/mes | "
                    f"Si el tráfico es bajo, considerar eliminar o reemplazar con VPC endpoints."
                ),
                estimated_monthly_savings=round(total_mo, 2),
            )
            count += 1
        else:
            resolve_finding(client_id, aws_account_id, gw.resource_id, finding_type)

    return count
