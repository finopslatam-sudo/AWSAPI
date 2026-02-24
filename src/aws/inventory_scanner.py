from datetime import datetime
from sqlalchemy.dialects.postgresql import insert

from src.models.database import db
from src.models.aws_resource_inventory import AWSResourceInventory


class InventoryScanner:

    def __init__(self, session, client_id, aws_account):
        self.session = session
        self.client_id = client_id
        self.aws_account = aws_account
        self.region = session.region_name

    # =====================================================
    # PUBLIC ENTRYPOINT
    # =====================================================
    def run(self):

        # 1️⃣ Marcar recursos existentes como inactivos
        # Esto evita "ghost resources"
        AWSResourceInventory.query.filter_by(
            client_id=self.client_id,
            aws_account_id=self.aws_account.id
        ).update({
            "is_active": False,
            "updated_at": datetime.utcnow()
        })

        # 2️⃣ Ejecutar scans
        self.scan_ec2()
        self.scan_ebs()
        self.scan_s3()

        # 3️⃣ Commit final
        db.session.commit()

    # =====================================================
    # UPSERT CENTRALIZADO ENTERPRISE
    # =====================================================
    def upsert_resource(
        self,
        service_name,
        resource_type,
        resource_id,
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
            region=self.region,
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
    def scan_ec2(self):

        ec2 = self.session.client("ec2")
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
                        state=instance.get("State", {}).get("Name"),
                        tags=tags,
                        resource_metadata={
                            "instance_type": instance.get("InstanceType"),
                            "launch_time": str(instance.get("LaunchTime")),
                            "availability_zone": instance.get("Placement", {}).get("AvailabilityZone"),
                            "private_ip": instance.get("PrivateIpAddress"),
                            "public_ip": instance.get("PublicIpAddress")
                        }
                    )

    # =====================================================
    # EBS
    # =====================================================
    def scan_ebs(self):

        ec2 = self.session.client("ec2")
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
                    state=volume.get("State"),
                    tags=tags,
                    resource_metadata={
                        "size_gb": volume.get("Size"),
                        "volume_type": volume.get("VolumeType"),
                        "availability_zone": volume.get("AvailabilityZone"),
                        "encrypted": volume.get("Encrypted"),
                        "iops": volume.get("Iops")
                    }
                )

    # =====================================================
    # S3
    # =====================================================
    def scan_s3(self):

        s3 = self.session.client("s3")
        buckets = s3.list_buckets()

        for bucket in buckets.get("Buckets", []):

            self.upsert_resource(
                service_name="S3",
                resource_type="Bucket",
                resource_id=bucket["Name"],
                state="active",
                tags={},  # opcional: se puede expandir con get_bucket_tagging
                resource_metadata={
                    "creation_date": str(bucket.get("CreationDate"))
                }
            )