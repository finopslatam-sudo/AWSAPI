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

        # 🔹 Cargar cuenta (solo para credenciales)
        aws_account = AWSAccount.query.get(aws_account_id)

        if not aws_account:
            raise Exception("AWS account not found")

        # 🔹 Obtener credenciales STS
        sts_service = STSService(aws_account)
        credentials = sts_service.assume_role()

        # 🔹 Crear sesión boto3 propia
        self.aws_session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

    # =====================================================
    # PUBLIC ENTRYPOINT (RECONCILIATION + MULTI REGION)
    # =====================================================
    def run(self):

        logger.info(f"Inventory started | client_id={self.client_id}")
        now = datetime.utcnow()

        try:
            # 1️⃣ Reconciliation
            AWSResourceInventory.query.filter_by(
                client_id=self.client_id,
                aws_account_id=self.aws_account_id
            ).update({
                "is_active": False,
                "updated_at": now
            })

            db.session.commit()
            db.session.expunge_all()

            # 2️⃣ Regiones activas
            regions = self.get_enabled_regions()

            # 3️⃣ Escaneo regional
            for region in regions:

                logger.info(f"Scanning region {region} | client_id={self.client_id}")

                self.scan_ec2(region)
                self.scan_ebs(region)
                self.scan_rds(region)
                self.scan_lambda(region)
                self.scan_dynamodb(region)
                self.scan_cloudwatch_logs(region)

                db.session.commit()
                db.session.expunge_all()

                logger.info(f"Region committed {region} | client_id={self.client_id}")

            # 4️⃣ Servicios globales
            self.scan_s3()

            db.session.commit()
            db.session.expunge_all()

            logger.info(f"Inventory completed | client_id={self.client_id}")

        except Exception:
            logger.exception(
                f"Inventory critical failure | client_id={self.client_id}"
            )
            raise

    # =====================================================
    # REGIONES ACTIVAS
    # =====================================================
    def get_enabled_regions(self):

        try:
            ec2 = self.aws_session.client("ec2", region_name="us-east-1")
            response = ec2.describe_regions(AllRegions=False)
            return [r["RegionName"] for r in response["Regions"]]

        except Exception:
            logger.exception("Failed to retrieve enabled regions")
            raise

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

        try:
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

        except Exception:
            logger.exception(f"EC2 scan failed | region={region}")
            raise

    # =====================================================
    # EBS
    # =====================================================
    def scan_ebs(self, region):

        try:
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

        except Exception:
            logger.exception(f"EBS scan failed | region={region}")
            raise

    # =====================================================
    # S3 (GLOBAL)
    # =====================================================
    def scan_s3(self):

        try:
            s3 = self.aws_session.client("s3")
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

        except Exception:
            logger.exception("S3 scan failed")
            raise

    # =====================================================
    # RDS
    # =====================================================
    def scan_rds(self, region):

        try:
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

        except Exception:
            logger.exception(f"RDS scan failed | region={region}")
            raise