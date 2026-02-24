from datetime import datetime
from sqlalchemy.dialects.postgresql import insert
import boto3

from src.models.database import db
from src.models.aws_resource_inventory import AWSResourceInventory


class InventoryScanner:

    def __init__(self, session, client_id, aws_account):
        self.session = session
        self.client_id = client_id
        self.aws_account = aws_account

    # =====================================================
    # PUBLIC ENTRYPOINT (RECONCILIATION + MULTI REGION)
    # =====================================================
    def run(self):

        now = datetime.utcnow()

        # 1️⃣ Reconciliation: marcar todo inactivo
        AWSResourceInventory.query.filter_by(
            client_id=self.client_id,
            aws_account_id=self.aws_account.id
        ).update({
            "is_active": False,
            "updated_at": now
        })

        db.session.flush()

        # 2️⃣ Detectar regiones activas
        regions = self.get_enabled_regions()

        # 3️⃣ Escaneo regional
        for region in regions:
            self.scan_ec2(region)
            self.scan_ebs(region)
            self.scan_rds(region)
            self.scan_lambda(region)
            self.scan_dynamodb(region)
            self.scan_cloudwatch_logs(region)

        # 4️⃣ Servicios globales
        self.scan_s3()

        db.session.commit()

    # =====================================================
    # REGIONES ACTIVAS
    # =====================================================
    def get_enabled_regions(self):

        ec2 = self.session.client("ec2", region_name="us-east-1")
        response = ec2.describe_regions(AllRegions=False)

        return [r["RegionName"] for r in response["Regions"]]

    # =====================================================
    # UPSERT ENTERPRISE
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
    # EC2
    # =====================================================
    def scan_ec2(self, region):

        try:
            ec2 = self.session.client("ec2", region_name=region)
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
        except Exception as e:
            print(f"[EC2] {region}: {e}")

    # =====================================================
    # EBS
    # =====================================================
    def scan_ebs(self, region):

        try:
            ec2 = self.session.client("ec2", region_name=region)
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
        except Exception as e:
            print(f"[EBS] {region}: {e}")

    # =====================================================
    # S3 (GLOBAL)
    # =====================================================
    def scan_s3(self):

        try:
            s3 = self.session.client("s3")
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
        except Exception as e:
            print(f"[S3] global: {e}")

    # =====================================================
    # RDS
    # =====================================================
    def scan_rds(self, region):

        try:
            rds = self.session.client("rds", region_name=region)
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
        except Exception as e:
            print(f"[RDS] {region}: {e}")