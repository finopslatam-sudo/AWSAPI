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

    # ================================
    # PUBLIC ENTRYPOINT
    # ================================
    def run(self):

        self.scan_ec2()
        self.scan_ebs()
        self.scan_s3()

        db.session.commit()

    # ================================
    # UPSERT CENTRALIZADO
    # ================================
    def upsert_resource(
        self,
        resource_id,
        resource_type,
        state=None,
        tags=None,
        metadata=None
    ):

        stmt = insert(AWSResourceInventory).values(
            client_id=self.client_id,
            aws_account_id=self.aws_account.id,
            resource_id=resource_id,
            resource_type=resource_type,
            region=self.region,
            state=state,
            tags=tags or {},
            metadata=metadata or {},
            detected_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
            is_active=True
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["client_id", "resource_id"],
            set_={
                "state": state,
                "tags": tags or {},
                "metadata": metadata or {},
                "last_seen_at": datetime.utcnow(),
                "is_active": True,
                "updated_at": datetime.utcnow()
            }
        )

        db.session.execute(stmt)

    # ================================
    # EC2
    # ================================
    def scan_ec2(self):

        ec2 = self.session.client("ec2")
        response = ec2.describe_instances()

        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:

                tags = {
                    tag["Key"]: tag["Value"]
                    for tag in instance.get("Tags", [])
                }

                self.upsert_resource(
                    resource_id=instance["InstanceId"],
                    resource_type="EC2",
                    state=instance["State"]["Name"],
                    tags=tags,
                    metadata={
                        "instance_type": instance["InstanceType"],
                        "launch_time": str(instance["LaunchTime"])
                    }
                )

    # ================================
    # EBS
    # ================================
    def scan_ebs(self):

        ec2 = self.session.client("ec2")
        response = ec2.describe_volumes()

        for volume in response["Volumes"]:

            tags = {
                tag["Key"]: tag["Value"]
                for tag in volume.get("Tags", [])
            }

            self.upsert_resource(
                resource_id=volume["VolumeId"],
                resource_type="EBS",
                state=volume["State"],
                tags=tags,
                metadata={
                    "size": volume["Size"],
                    "volume_type": volume["VolumeType"]
                }
            )

    # ================================
    # S3
    # ================================
    def scan_s3(self):

        s3 = self.session.client("s3")
        buckets = s3.list_buckets()

        for bucket in buckets["Buckets"]:

            self.upsert_resource(
                resource_id=bucket["Name"],
                resource_type="S3",
                state="active",
                tags={},
                metadata={
                    "creation_date": str(bucket["CreationDate"])
                }
            )