import logging
from datetime import datetime
import boto3
from sqlalchemy.dialects.postgresql import insert

from src.models.database import db
from src.models.aws_account import AWSAccount
from src.models.aws_resource_inventory import AWSResourceInventory
from src.aws.sts_service import STSService


logger = logging.getLogger(__name__)


class InventoryScanner:

    def __init__(self, client_id, aws_account_id):
        self.client_id = client_id
        self.aws_account_id = aws_account_id

        # 🔹 Cargar cuenta
        aws_account = AWSAccount.query.get(aws_account_id)
        if not aws_account:
            raise Exception("AWS account not found")

        # 🔹 Obtener credenciales STS (FORMA CORRECTA)
        sts_service = STSService()

        credentials = sts_service.assume_role(
            role_arn=aws_account.role_arn,
            external_id=aws_account.external_id,
            session_name="finops-inventory"
        )

        # 🔹 Crear sesión boto3
        self.aws_session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

    # =====================================================
    # PUBLIC ENTRYPOINT
    # =====================================================
    def run(self):

        logger.info(f"Inventory started | client_id={self.client_id}")
        now = datetime.utcnow()

        # 1️⃣ Desactivar recursos anteriores
        AWSResourceInventory.query.filter_by(
            client_id=self.client_id,
            aws_account_id=self.aws_account_id
        ).update({
            "is_active": False,
            "updated_at": now
        })

        db.session.commit()
        db.session.expunge_all()

        # 2️⃣ Obtener regiones
        regions = self.get_enabled_regions()

        # 3️⃣ Scans regionales protegidos
        for region in regions:

            logger.info(f"Scanning region {region}")

            services = [
                ("EC2", self.scan_ec2),
                ("EBS", self.scan_ebs),
                ("RDS", self.scan_rds),
                ("Lambda", self.scan_lambda),
                ("DynamoDB", self.scan_dynamodb),
                ("CloudWatchLogs", self.scan_cloudwatch_logs),
                ("NAT", self.scan_nat_gateways),
                ("ECS", self.scan_ecs),
                ("Redshift", self.scan_redshift),
                ("EKS", self.scan_eks),
            ]

            for service_name, service_method in services:
                try:
                    service_method(region)
                except Exception:
                    logger.exception(
                        f"{service_name} scan failed | region={region} | client_id={self.client_id}"
                    )

            db.session.commit()
            db.session.expunge_all()

        # 4️⃣ Servicio global S3
        try:
            self.scan_s3()
        except Exception:
            logger.exception(
                f"S3 scan failed | client_id={self.client_id}"
            )

        db.session.commit()
        db.session.expunge_all()

        logger.info("Inventory completed")

    # =====================================================
    def get_enabled_regions(self):

        ec2 = self.aws_session.client("ec2", region_name="us-east-1")
        response = ec2.describe_regions(AllRegions=False)
        return [r["RegionName"] for r in response["Regions"]]

    # =====================================================
    def upsert_resource(
        self,
        service_name,
        resource_type,
        resource_id,
        region,
        state=None,
        tags=None,
        resource_metadata=None
    ):

        now = datetime.utcnow()

        stmt = insert(AWSResourceInventory).values(
            client_id=self.client_id,
            aws_account_id=self.aws_account_id,
            service_name=service_name,
            resource_type=resource_type,
            resource_id=resource_id,
            region=region,
            state=state,
            tags=tags or {},
            resource_metadata=resource_metadata or {},
            detected_at=now,
            last_seen_at=now,
            is_active=True,
            created_at=now,
            updated_at=now
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["client_id", "resource_id"],
            set_={
                "service_name": service_name,
                "resource_type": resource_type,
                "region": region,
                "state": state,
                "tags": tags or {},
                "resource_metadata": resource_metadata or {},
                "last_seen_at": now,
                "is_active": True,
                "updated_at": now
            }
        )

        db.session.execute(stmt)

    # =====================================================
    # EC2
    # =====================================================
    def scan_ec2(self, region):

        ec2 = self.aws_session.client("ec2", region_name=region)
        paginator = ec2.get_paginator("describe_instances")

        for page in paginator.paginate():
            for reservation in page.get("Reservations", []):
                for instance in reservation.get("Instances", []):

                    tags = {
                        tag["Key"]: tag["Value"]
                        for tag in instance.get("Tags", [])
                    }

                    self.upsert_resource(
                        service_name="EC2",
                        resource_type="Instance",
                        resource_id=instance["InstanceId"],
                        region=region,
                        state=instance.get("State", {}).get("Name"),
                        tags=tags,
                        resource_metadata={
                            "instance_type": instance.get("InstanceType"),
                            "availability_zone": instance.get("Placement", {}).get("AvailabilityZone"),
                            "private_ip": instance.get("PrivateIpAddress"),
                            "public_ip": instance.get("PublicIpAddress")
                        }
                    )

    # =====================================================
    # EBS
    # =====================================================
    def scan_ebs(self, region):

        ec2 = self.aws_session.client("ec2", region_name=region)
        paginator = ec2.get_paginator("describe_volumes")

        for page in paginator.paginate():
            for volume in page.get("Volumes", []):

                tags = {
                    tag["Key"]: tag["Value"]
                    for tag in volume.get("Tags", [])
                }

                self.upsert_resource(
                    service_name="EBS",
                    resource_type="Volume",
                    resource_id=volume["VolumeId"],
                    region=region,
                    state=volume.get("State"),
                    tags=tags,
                    resource_metadata={
                        "size_gb": volume.get("Size"),
                        "volume_type": volume.get("VolumeType"),
                        "availability_zone": volume.get("AvailabilityZone"),
                        "encrypted": volume.get("Encrypted")
                    }
                )

    # =====================================================
    # RDS
    # =====================================================
    def scan_rds(self, region):

        rds = self.aws_session.client("rds", region_name=region)
        paginator = rds.get_paginator("describe_db_instances")

        for page in paginator.paginate():
            for db_instance in page.get("DBInstances", []):

                self.upsert_resource(
                    service_name="RDS",
                    resource_type="DBInstance",
                    resource_id=db_instance["DBInstanceIdentifier"],
                    region=region,
                    state=db_instance.get("DBInstanceStatus"),
                    tags={},
                    resource_metadata={
                        "engine": db_instance.get("Engine"),
                        "instance_class": db_instance.get("DBInstanceClass"),
                        "allocated_storage": db_instance.get("AllocatedStorage"),
                        "multi_az": db_instance.get("MultiAZ"),
                        "publicly_accessible": db_instance.get("PubliclyAccessible")
                    }
                )
    # =====================================================
    # LAMBDA
    # =====================================================
    def scan_lambda(self, region):

        try:
            lambda_client = self.aws_session.client("lambda", region_name=region)
            paginator = lambda_client.get_paginator("list_functions")

            for page in paginator.paginate():
                for function in page.get("Functions", []):

                    self.upsert_resource(
                        service_name="Lambda",
                        resource_type="Function",
                        resource_id=function["FunctionName"],
                        region=region,
                        state="active",
                        tags={},
                        resource_metadata={
                            "runtime": function.get("Runtime"),
                            "handler": function.get("Handler"),
                            "memory_size": function.get("MemorySize"),
                            "timeout": function.get("Timeout"),
                            "last_modified": function.get("LastModified"),
                        }
                    )

        except Exception:
            logger.exception(f"Lambda scan failed | region={region}")
            raise

    # =====================================================
    # DYNAMODB
    # =====================================================
    def scan_dynamodb(self, region):

        try:
            dynamodb = self.aws_session.client("dynamodb", region_name=region)
            paginator = dynamodb.get_paginator("list_tables")

            for page in paginator.paginate():
                for table_name in page.get("TableNames", []):

                    table = dynamodb.describe_table(TableName=table_name)["Table"]

                    self.upsert_resource(
                        service_name="DynamoDB",
                        resource_type="Table",
                        resource_id=table_name,
                        region=region,
                        state=table.get("TableStatus"),
                        tags={},
                        resource_metadata={
                            "billing_mode": table.get("BillingModeSummary", {}).get("BillingMode"),
                            "item_count": table.get("ItemCount"),
                            "table_size_bytes": table.get("TableSizeBytes"),
                            "creation_date": str(table.get("CreationDateTime")),
                        }
                    )

        except Exception:
            logger.exception(f"DynamoDB scan failed | region={region}")
            raise
    
    # =====================================================
    # CLOUDWATCH LOGS
    # =====================================================
    def scan_cloudwatch_logs(self, region):

        try:
            logs_client = self.aws_session.client("logs", region_name=region)
            paginator = logs_client.get_paginator("describe_log_groups")

            for page in paginator.paginate():
                for log_group in page.get("logGroups", []):

                    self.upsert_resource(
                        service_name="CloudWatch",
                        resource_type="LogGroup",
                        resource_id=log_group["logGroupName"],
                        region=region,
                        state="active",
                        tags={},
                        resource_metadata={
                            "stored_bytes": log_group.get("storedBytes"),
                            "retention_days": log_group.get("retentionInDays"),
                            "creation_time": log_group.get("creationTime"),
                        }
                    )

        except Exception:
            logger.exception(f"CloudWatch Logs scan failed | region={region}")
            raise

    # =====================================================
    # S3 (GLOBAL SERVICE)
    # =====================================================
    def scan_s3(self):

        s3 = self.aws_session.client("s3")
        response = s3.list_buckets()

        for bucket in response.get("Buckets", []):

            bucket_name = bucket["Name"]

            # Obtener región del bucket
            try:
                location = s3.get_bucket_location(Bucket=bucket_name)
                region = location.get("LocationConstraint") or "us-east-1"
            except Exception:
                region = "unknown"

            self.upsert_resource(
                service_name="S3",
                resource_type="Bucket",
                resource_id=bucket_name,
                region=region,
                state="active",
                tags={},
                resource_metadata={
                    "creation_date": str(bucket.get("CreationDate"))
                }
            )

    # =====================================================
    # NAT GATEWAY
    # =====================================================
    def scan_nat_gateways(self, region):

        try:
            ec2 = self.aws_session.client("ec2", region_name=region)
            paginator = ec2.get_paginator("describe_nat_gateways")

            for page in paginator.paginate():
                for nat in page.get("NatGateways", []):

                    tags = {
                        tag["Key"]: tag["Value"]
                        for tag in nat.get("Tags", [])
                    }

                    self.upsert_resource(
                        service_name="NAT",
                        resource_type="NatGateway",
                        resource_id=nat["NatGatewayId"],
                        region=region,
                        state=nat.get("State"),
                        tags=tags,
                        resource_metadata={
                            "subnet_id": nat.get("SubnetId"),
                            "vpc_id": nat.get("VpcId"),
                            "connectivity_type": nat.get("ConnectivityType"),
                            "creation_time": str(nat.get("CreateTime"))
                        }
                    )

        except Exception:
            logger.exception(f"NAT Gateway scan failed | region={region}")
            raise

    # =====================================================
    # ECS
    # =====================================================
    def scan_ecs(self, region):

        try:
            ecs = self.aws_session.client("ecs", region_name=region)

            # 1️⃣ Listar clusters
            cluster_arns = ecs.list_clusters().get("clusterArns", [])

            for cluster_arn in cluster_arns:

                cluster_details = ecs.describe_clusters(
                    clusters=[cluster_arn]
                )["clusters"][0]

                cluster_name = cluster_details.get("clusterName")

                self.upsert_resource(
                    service_name="ECS",
                    resource_type="Cluster",
                    resource_id=cluster_name,
                    region=region,
                    state="active",
                    tags={},
                    resource_metadata={
                        "status": cluster_details.get("status"),
                        "running_tasks": cluster_details.get("runningTasksCount"),
                        "pending_tasks": cluster_details.get("pendingTasksCount"),
                        "active_services": cluster_details.get("activeServicesCount"),
                    }
                )

                # 2️⃣ Listar servicios dentro del cluster
                service_arns = ecs.list_services(
                    cluster=cluster_arn
                ).get("serviceArns", [])

                if service_arns:
                    services = ecs.describe_services(
                        cluster=cluster_arn,
                        services=service_arns
                    )["services"]

                    for service in services:

                        self.upsert_resource(
                            service_name="ECS",
                            resource_type="Service",
                            resource_id=service.get("serviceName"),
                            region=region,
                            state=service.get("status"),
                            tags={},
                            resource_metadata={
                                "desired_count": service.get("desiredCount"),
                                "running_count": service.get("runningCount"),
                                "pending_count": service.get("pendingCount"),
                                "launch_type": service.get("launchType"),
                            }
                        )

        except Exception:
            logger.exception(f"ECS scan failed | region={region}")
            raise

    # =====================================================
    # REDSHIFT
    # =====================================================
    def scan_redshift(self, region):

        try:
            redshift = self.aws_session.client("redshift", region_name=region)
            paginator = redshift.get_paginator("describe_clusters")

            for page in paginator.paginate():
                for cluster in page.get("Clusters", []):

                    self.upsert_resource(
                        service_name="Redshift",
                        resource_type="Cluster",
                        resource_id=cluster["ClusterIdentifier"],
                        region=region,
                        state=cluster.get("ClusterStatus"),
                        tags={},
                        resource_metadata={
                            "node_type": cluster.get("NodeType"),
                            "cluster_type": cluster.get("ClusterType"),
                            "number_of_nodes": cluster.get("NumberOfNodes"),
                            "encrypted": cluster.get("Encrypted"),
                            "publicly_accessible": cluster.get("PubliclyAccessible"),
                        }
                    )

        except Exception:
            logger.exception(f"Redshift scan failed | region={region}")
            raise

    # =====================================================
    # EKS
    # =====================================================
    def scan_eks(self, region):

        try:
            eks = self.aws_session.client("eks", region_name=region)

            # 1️⃣ Listar clusters
            cluster_names = eks.list_clusters().get("clusters", [])

            for cluster_name in cluster_names:

                cluster = eks.describe_cluster(name=cluster_name)["cluster"]

                self.upsert_resource(
                    service_name="EKS",
                    resource_type="Cluster",
                    resource_id=cluster_name,
                    region=region,
                    state=cluster.get("status"),
                    tags={},
                    resource_metadata={
                        "version": cluster.get("version"),
                        "endpoint": cluster.get("endpoint"),
                        "platform_version": cluster.get("platformVersion"),
                    }
                )

                # 2️⃣ Listar nodegroups
                nodegroups = eks.list_nodegroups(
                    clusterName=cluster_name
                ).get("nodegroups", [])

                for nodegroup_name in nodegroups:

                    nodegroup = eks.describe_nodegroup(
                        clusterName=cluster_name,
                        nodegroupName=nodegroup_name
                    )["nodegroup"]

                    self.upsert_resource(
                        service_name="EKS",
                        resource_type="NodeGroup",
                        resource_id=nodegroup_name,
                        region=region,
                        state=nodegroup.get("status"),
                        tags={},
                        resource_metadata={
                            "instance_types": nodegroup.get("instanceTypes"),
                            "min_size": nodegroup.get("scalingConfig", {}).get("minSize"),
                            "max_size": nodegroup.get("scalingConfig", {}).get("maxSize"),
                            "desired_size": nodegroup.get("scalingConfig", {}).get("desiredSize"),
                            "capacity_type": nodegroup.get("capacityType"),
                        }
                    )

        except Exception:
            logger.exception(f"EKS scan failed | region={region}")
            raise
