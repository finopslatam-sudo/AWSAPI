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

        self.scan_ec2()
        self.scan_ebs()
        self.scan_s3()

        db.session.commit()

    # =====================================================
    # UPSERT CENTRALIZADO (ENTERPRISE SAFE)
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
        response = ec2.describe_instances()

        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):

                tags = {
                    tag["Key"]: tag["Value"]
                    for tag in instance.get("Tags", [])
                }

                self.upsert_resource(
                    service_name="EC2",
                    resource_type="Instance",
                    resource_id=instance["InstanceId"],
                    state=instance["State"]["Name"],
                    tags=tags,
                    resource_metadata={
                        "instance_type": instance["InstanceType"],
                        "launch_time": str(instance["LaunchTime"]),
                        "availability_zone": instance["Placement"]["AvailabilityZone"]
                    }
                )

    # =====================================================
    # EBS
    # =====================================================
    def scan_ebs(self):

        ec2 = self.session.client("ec2")
        response = ec2.describe_volumes()

        for volume in response.get("Volumes", []):

            tags = {
                tag["Key"]: tag["Value"]
                for tag in volume.get("Tags", [])
            }

            self.upsert_resource(
                service_name="EBS",
                resource_type="Volume",
                resource_id=volume["VolumeId"],
                state=volume["State"],
                tags=tags,
                resource_metadata={
                    "size_gb": volume["Size"],
                    "volume_type": volume["VolumeType"],
                    "availability_zone": volume["AvailabilityZone"],
                    "encrypted": volume["Encrypted"]
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
                tags={},  # se puede mejorar con get_bucket_tagging
                resource_metadata={
                    "creation_date": str(bucket["CreationDate"])
                }
            )