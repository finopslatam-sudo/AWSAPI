import boto3
from datetime import datetime, timedelta
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding
from src.aws.sts_service import STSService
from src.models.aws_account import AWSAccount


class RightsizingEngine:

    EC2_CPU_THRESHOLD = 10.0
    RDS_CPU_THRESHOLD = 10.0
    REDSHIFT_CPU_THRESHOLD = 10.0
    LAMBDA_LOW_INVOCATIONS_THRESHOLD = 100
    NAT_LOW_TRAFFIC_BYTES = 1_000_000_000
    CLOUDWATCH_MIN_STORED_BYTES = 1_000_000_000

    @staticmethod
    def run(client_id, aws_account_id=None):

        accounts_query = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        )

        if aws_account_id is not None:
            accounts_query = accounts_query.filter_by(id=aws_account_id)

        aws_accounts = accounts_query.all()

        if not aws_accounts:
            return 0

        sts = STSService()
        total = 0

        for aws_account in aws_accounts:
            credentials = sts.assume_role(
                role_arn=aws_account.role_arn,
                external_id=aws_account.external_id,
                session_name=f"finops-rightsizing-{aws_account.id}"
            )

            session = boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
            )

            total += RightsizingEngine.evaluate_ec2(
                session,
                client_id,
                aws_account.id
            )
            total += RightsizingEngine.evaluate_ebs(
                client_id,
                aws_account.id
            )
            total += RightsizingEngine.evaluate_rds(
                session,
                client_id,
                aws_account.id
            )
            total += RightsizingEngine.evaluate_lambda(
                session,
                client_id,
                aws_account.id
            )
            total += RightsizingEngine.evaluate_dynamodb(
                client_id,
                aws_account.id
            )
            total += RightsizingEngine.evaluate_cloudwatch(
                client_id,
                aws_account.id
            )
            total += RightsizingEngine.evaluate_nat(
                session,
                client_id,
                aws_account.id
            )
            total += RightsizingEngine.evaluate_redshift(
                session,
                client_id,
                aws_account.id
            )

        return total

    @staticmethod
    def _resolve_finding(client_id, aws_account_id, resource_id, finding_type):
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

    @staticmethod
    def _upsert_recommendation(
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

    @staticmethod
    def _get_metric_sum(
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

    @staticmethod
    def _get_metric_average(
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

    # =====================================================
    # EC2 RIGHTSIZING
    # =====================================================
    @staticmethod
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
                RightsizingEngine._resolve_finding(
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
                avg_cpu = RightsizingEngine._get_metric_average(
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
                RightsizingEngine._resolve_finding(
                    client_id,
                    aws_account_id,
                    instance_id,
                    finding_type
                )
                continue

            if avg_cpu < RightsizingEngine.EC2_CPU_THRESHOLD:
                RightsizingEngine._upsert_recommendation(
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
                RightsizingEngine._resolve_finding(
                    client_id,
                    aws_account_id,
                    instance_id,
                    finding_type
                )

        return count

    # =====================================================
    # EBS RIGHTSIZING
    # =====================================================
    @staticmethod
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

                RightsizingEngine._upsert_recommendation(
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
                RightsizingEngine._resolve_finding(
                    client_id,
                    aws_account_id,
                    volume.resource_id,
                    finding_type
                )

        return count

    # =====================================================
    # RDS RIGHTSIZING
    # =====================================================
    @staticmethod
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
                RightsizingEngine._resolve_finding(
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
                avg_cpu = RightsizingEngine._get_metric_average(
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
                RightsizingEngine._resolve_finding(
                    client_id,
                    aws_account_id,
                    db_identifier,
                    finding_type
                )
                continue

            if avg_cpu < RightsizingEngine.RDS_CPU_THRESHOLD:
                RightsizingEngine._upsert_recommendation(
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
                RightsizingEngine._resolve_finding(
                    client_id,
                    aws_account_id,
                    db_identifier,
                    finding_type
                )

        return count

    # =====================================================
    # LAMBDA RIGHTSIZING
    # =====================================================
    @staticmethod
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
                RightsizingEngine._resolve_finding(
                    client_id,
                    aws_account_id,
                    function.resource_id,
                    finding_type
                )
                continue

            try:
                cloudwatch = session.client("cloudwatch", region_name=function.region)
                total_invocations = RightsizingEngine._get_metric_sum(
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

            if total_invocations is not None and total_invocations < RightsizingEngine.LAMBDA_LOW_INVOCATIONS_THRESHOLD:
                estimated_savings = round(max((memory_size - 1024) / 1024 * 3, 0), 2)
                RightsizingEngine._upsert_recommendation(
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
                RightsizingEngine._resolve_finding(
                    client_id,
                    aws_account_id,
                    function.resource_id,
                    finding_type
                )

        return count

    # =====================================================
    # DYNAMODB RIGHTSIZING
    # =====================================================
    @staticmethod
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
                RightsizingEngine._upsert_recommendation(
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
                RightsizingEngine._resolve_finding(
                    client_id,
                    aws_account_id,
                    table.resource_id,
                    finding_type
                )

        return count

    # =====================================================
    # CLOUDWATCH STORAGE OPTIMIZATION
    # =====================================================
    @staticmethod
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
                stored_bytes >= RightsizingEngine.CLOUDWATCH_MIN_STORED_BYTES and
                (retention_days is None or retention_days > 90)
            )

            if qualifies:
                stored_gb = stored_bytes / (1024 ** 3)
                estimated_savings = round(min(max(stored_gb * 0.03, 1.0), 20.0), 2)
                retention_label = "sin retencion definida" if retention_days is None else f"con retencion de {retention_days} dias"

                RightsizingEngine._upsert_recommendation(
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
                RightsizingEngine._resolve_finding(
                    client_id,
                    aws_account_id,
                    log_group.resource_id,
                    finding_type
                )

        return count

    # =====================================================
    # NAT GATEWAY OPTIMIZATION
    # =====================================================
    @staticmethod
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
                RightsizingEngine._resolve_finding(
                    client_id,
                    aws_account_id,
                    gateway.resource_id,
                    finding_type
                )
                continue

            try:
                cloudwatch = session.client("cloudwatch", region_name=gateway.region)
                bytes_out = RightsizingEngine._get_metric_sum(
                    cloudwatch=cloudwatch,
                    namespace="AWS/NATGateway",
                    metric_name="BytesOutToDestination",
                    dimensions=[
                        {"Name": "NatGatewayId", "Value": gateway.resource_id}
                    ],
                    start=start,
                    end=end
                ) or 0
                bytes_in = RightsizingEngine._get_metric_sum(
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

            if total_bytes < RightsizingEngine.NAT_LOW_TRAFFIC_BYTES:
                RightsizingEngine._upsert_recommendation(
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
                RightsizingEngine._resolve_finding(
                    client_id,
                    aws_account_id,
                    gateway.resource_id,
                    finding_type
                )

        return count

    # =====================================================
    # REDSHIFT RIGHTSIZING
    # =====================================================
    @staticmethod
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
                RightsizingEngine._resolve_finding(
                    client_id,
                    aws_account_id,
                    cluster.resource_id,
                    finding_type
                )
                continue

            try:
                cloudwatch = session.client("cloudwatch", region_name=cluster.region)
                avg_cpu = RightsizingEngine._get_metric_average(
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

            if avg_cpu is not None and avg_cpu < RightsizingEngine.REDSHIFT_CPU_THRESHOLD:
                node_count = (cluster.resource_metadata or {}).get("number_of_nodes") or 1
                estimated_savings = round(max(float(node_count) * 30.0, 30.0), 2)
                RightsizingEngine._upsert_recommendation(
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
                RightsizingEngine._resolve_finding(
                    client_id,
                    aws_account_id,
                    cluster.resource_id,
                    finding_type
                )

        return count
