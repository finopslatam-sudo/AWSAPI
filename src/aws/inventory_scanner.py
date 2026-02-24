from datetime import datetime
from sqlalchemy.dialects.postgresql import insert
import boto3

from src.models.database import db
from src.models.aws_resource_inventory import AWSResourceInventory


class InventoryScanner:

    def __init__(self, session, client_id, aws_account):
        self.base_session = session
        self.client_id = client_id
        self.aws_account = aws_account

    # =====================================================
    # PUBLIC ENTRYPOINT (MULTI-REGIÓN)
    # =====================================================
    def run(self):

        # 1️⃣ Marcar todo como inactivo antes de escanear
        AWSResourceInventory.query.filter_by(
            client_id=self.client_id,
            aws_account_id=self.aws_account.id
        ).update({
            "is_active": False,
            "updated_at": datetime.utcnow()
        })

        # 2️⃣ Detectar regiones habilitadas
        regions = self.get_enabled_regions()

        # 3️⃣ Escanear servicios regionales
        for region in regions:
            regional_session = boto3.Session(
                aws_access_key_id=self.base_session.get_credentials().access_key,
                aws_secret_access_key=self.base_session.get_credentials().secret_key,
                aws_session_token=self.base_session.get_credentials().token,
                region_name=region
            )

            self.scan_ec2(regional_session, region)
            self.scan_ebs(regional_session, region)
            self.scan_rds(regional_session, region)
            self.scan_lambda(regional_session, region)
            self.scan_dynamodb(regional_session, region)
            self.scan_cloudwatch_logs(regional_session, region)

        # 4️⃣ Escanear servicios globales (una sola vez)
        self.scan_s3(self.base_session)

        db.session.commit()

    # =====================================================
    # DETECTAR REGIONES ACTIVAS
    # =====================================================
    def get_enabled_regions(self):

        ec2 = self.base_session.client("ec2", region_name="us-east-1")

        response = ec2.describe_regions(AllRegions=False)

        return [r["RegionName"] for r in response["Regions"]]

    # =====================================================
    # UPSERT
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
            aws_account_id=self.aws_account.id,
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
    # EC2 (REGIONAL)
    # =====================================================
    def scan_ec2(self, session, region):

        ec2 = session.client("ec2")
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
    # EBS (REGIONAL)
    # =====================================================
    def scan_ebs(self, session, region):

        ec2 = session.client("ec2")
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
    # S3 (GLOBAL)
    # =====================================================
    def scan_s3(self, session):

        s3 = session.client("s3")
        buckets = s3.list_buckets()

        for bucket in buckets.get("Buckets", []):

            self.upsert_resource(
                service_name="S3",
                resource_type="Bucket",
                resource_id=bucket["Name"],
                region="global",
                state="active",
                tags={},
                resource_metadata={
                    "creation_date": str(bucket.get("CreationDate"))
                }
            )

    # =====================================================
    # RDS
    # =====================================================
    def scan_rds(self, session, region):

        rds = session.client("rds", region_name=region)
        response = rds.describe_db_instances()

        for db_instance in response.get("DBInstances", []):

            self.upsert_resource(
                service_name="RDS",
                resource_type="DBInstance",
                resource_id=db_instance["DBInstanceIdentifier"],
                region=region,
                state=db_instance["DBInstanceStatus"],
                tags={},  # se pueden agregar luego con list_tags
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
    def scan_lambda(self, session, region):

        try:
            lambda_client = session.client("lambda", region_name=region)
            response = lambda_client.list_functions()

            for function in response.get("Functions", []):

                self.upsert_resource(
                    service_name="Lambda",
                    resource_type="Function",
                    resource_id=function["FunctionName"],
                    region=region,
                    state="active",
                    tags={},  # opcional expandir con list_tags
                    resource_metadata={
                        "runtime": function.get("Runtime"),
                        "memory_size": function.get("MemorySize"),
                        "timeout": function.get("Timeout"),
                        "last_modified": function.get("LastModified")
                    }
                )

        except Exception as e:
            print(f"[Lambda] Error in region {region}: {e}")

    # =====================================================
    # DYNAMODB
    # =====================================================
    def scan_dynamodb(self, session, region):

        try:
            dynamodb = session.client("dynamodb", region_name=region)
            response = dynamodb.list_tables()

            for table_name in response.get("TableNames", []):

                table_info = dynamodb.describe_table(TableName=table_name)["Table"]

                self.upsert_resource(
                    service_name="DynamoDB",
                    resource_type="Table",
                    resource_id=table_name,
                    region=region,
                    state=table_info.get("TableStatus"),
                    tags={},  # opcional expandir con list_tags
                    resource_metadata={
                        "billing_mode": table_info.get("BillingModeSummary", {}).get("BillingMode"),
                        "item_count": table_info.get("ItemCount"),
                        "table_size_bytes": table_info.get("TableSizeBytes")
                    }
                )

        except Exception as e:
            print(f"[DynamoDB] Error in region {region}: {e}")

    # =====================================================
    # CLOUDWATCH LOG GROUPS
    # =====================================================
    def scan_cloudwatch_logs(self, session, region):

        try:
            logs = session.client("logs", region_name=region)
            response = logs.describe_log_groups()

            for log_group in response.get("logGroups", []):

                self.upsert_resource(
                    service_name="CloudWatch",
                    resource_type="LogGroup",
                    resource_id=log_group["logGroupName"],
                    region=region,
                    state="active",
                    tags={},
                    resource_metadata={
                        "retention_in_days": log_group.get("retentionInDays"),
                        "stored_bytes": log_group.get("storedBytes")
                    }
                )

        except Exception as e:
            print(f"[CloudWatch Logs] Error in region {region}: {e}")