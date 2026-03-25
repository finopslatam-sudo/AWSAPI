from datetime import datetime, timedelta
from src.models.aws_resource_inventory import AWSResourceInventory
from src.aws.finops.rightsizing.shared import (
    RDS_CPU_THRESHOLD,
    REDSHIFT_CPU_THRESHOLD,
    resolve_finding,
    upsert_recommendation,
    get_metric_average,
)
from src.aws.finops.rightsizing.pricing import (
    RDS_DOWNSIZE, rds_monthly,
    REDSHIFT_PRICING, REDSHIFT_DOWNSIZE, HOURS_MONTH,
)


# =====================================================
# RDS RIGHTSIZING — specific instance class downsize
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
            resolve_finding(client_id, aws_account_id, db_instance.resource_id, finding_type)
            continue

        region        = db_instance.region
        db_identifier = db_instance.resource_id
        metadata      = db_instance.resource_metadata or {}
        instance_class = metadata.get("instance_class", "")
        multi_az       = bool(metadata.get("multi_az", False))

        cloudwatch = session.client("cloudwatch", region_name=region)
        end   = datetime.utcnow()
        start = end - timedelta(days=7)

        try:
            avg_cpu = get_metric_average(
                cloudwatch=cloudwatch,
                namespace="AWS/RDS",
                metric_name="CPUUtilization",
                dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_identifier}],
                start=start,
                end=end,
            )
        except Exception as e:
            print(f"[RDS RIGHTSIZING ERROR]: {str(e)}")
            continue

        if avg_cpu is None:
            resolve_finding(client_id, aws_account_id, db_identifier, finding_type)
            continue

        if avg_cpu < RDS_CPU_THRESHOLD:
            recommended = RDS_DOWNSIZE.get(instance_class)
            current_mo  = rds_monthly(instance_class, multi_az)
            az_label    = " Multi-AZ" if multi_az else ""

            if recommended and current_mo > 0:
                rec_mo   = rds_monthly(recommended, multi_az)
                savings  = round(current_mo - rec_mo, 2)
                severity = "HIGH" if savings >= 100 else "MEDIUM"
                message  = (
                    f"CPU promedio 7d: {round(avg_cpu, 1)}% | "
                    f"Actual: {instance_class}{az_label} (${current_mo:.0f}/mes) → "
                    f"Recomendado: {recommended}{az_label} (${rec_mo:.0f}/mes) | "
                    f"Ahorro: ${savings:.0f}/mes"
                )
            else:
                savings  = round(max(current_mo * 0.5, 10.0), 2) if current_mo > 0 else 50.0
                severity = "MEDIUM"
                message  = (
                    f"CPU promedio 7d: {round(avg_cpu, 1)}% | "
                    f"Instancia {instance_class}{az_label} subutilizada. Evaluar downsize."
                )

            upsert_recommendation(
                client_id=client_id,
                aws_account_id=db_instance.aws_account_id,
                resource_id=db_identifier,
                resource_type="DBInstance",
                region=region,
                aws_service="RDS",
                finding_type=finding_type,
                severity=severity,
                message=message,
                estimated_monthly_savings=savings,
            )
            count += 1
        else:
            resolve_finding(client_id, aws_account_id, db_identifier, finding_type)

    return count


# =====================================================
# REDSHIFT RIGHTSIZING — reduce nodes or node type
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
    end   = datetime.utcnow()
    start = end - timedelta(days=7)

    for cluster in clusters:
        if cluster.state != "available":
            resolve_finding(client_id, aws_account_id, cluster.resource_id, finding_type)
            continue

        metadata   = cluster.resource_metadata or {}
        node_type  = metadata.get("node_type", "")
        node_count = int(metadata.get("number_of_nodes") or 1)

        try:
            cloudwatch = session.client("cloudwatch", region_name=cluster.region)
            avg_cpu = get_metric_average(
                cloudwatch=cloudwatch,
                namespace="AWS/Redshift",
                metric_name="CPUUtilization",
                dimensions=[{"Name": "ClusterIdentifier", "Value": cluster.resource_id}],
                start=start,
                end=end,
            )
        except Exception as e:
            print(f"[REDSHIFT RIGHTSIZING ERROR]: {str(e)}")
            continue

        if avg_cpu is None or avg_cpu >= REDSHIFT_CPU_THRESHOLD:
            resolve_finding(client_id, aws_account_id, cluster.resource_id, finding_type)
            continue

        node_hr   = REDSHIFT_PRICING.get(node_type, 0.0)
        current_mo = round(node_hr * node_count * HOURS_MONTH, 2)

        if node_count > 1:
            rec_count = node_count - 1
            savings   = round(node_hr * HOURS_MONTH, 2)
            message   = (
                f"CPU promedio 7d: {round(avg_cpu, 1)}% | "
                f"Cluster: {node_count}x {node_type} (${current_mo:.0f}/mes) → "
                f"Recomendado: {rec_count}x {node_type} (${current_mo - savings:.0f}/mes) | "
                f"Ahorro: ${savings:.0f}/mes"
            )
        elif REDSHIFT_DOWNSIZE.get(node_type):
            rec_type  = REDSHIFT_DOWNSIZE[node_type]
            rec_mo    = round(REDSHIFT_PRICING.get(rec_type, 0.0) * HOURS_MONTH, 2)
            savings   = round(max(current_mo - rec_mo, 0), 2)
            message   = (
                f"CPU promedio 7d: {round(avg_cpu, 1)}% | "
                f"Nodo: {node_type} (${current_mo:.0f}/mes) → "
                f"Recomendado: {rec_type} (${rec_mo:.0f}/mes) | "
                f"Ahorro: ${savings:.0f}/mes"
            )
        else:
            savings = round(current_mo * 0.3, 2)
            message = (
                f"CPU promedio 7d: {round(avg_cpu, 1)}% | "
                f"Cluster {node_type} ({node_count} nodo/s) subutilizado. "
                f"Evaluar reducir nodos o pausar el cluster."
            )

        upsert_recommendation(
            client_id=client_id,
            aws_account_id=aws_account_id,
            resource_id=cluster.resource_id,
            resource_type=cluster.resource_type,
            region=cluster.region,
            aws_service="Redshift",
            finding_type=finding_type,
            severity="MEDIUM",
            message=message,
            estimated_monthly_savings=savings,
        )
        count += 1

    return count
