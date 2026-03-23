import logging

from src.aws.scanners.shared import BaseScanner


logger = logging.getLogger(__name__)


class EC2Scanner(BaseScanner):
    """Handles EC2 instances, EBS volumes, NAT Gateways, and Reserved Instances."""

    # ------------------------------------------------------------------
    # EC2 INSTANCES
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # EBS VOLUMES
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # NAT GATEWAYS
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # RESERVED INSTANCES
    # ------------------------------------------------------------------
    def scan_reserved_instances(self, region):
        try:
            ec2 = self.aws_session.client("ec2", region_name=region)

            response = ec2.describe_reserved_instances(
                Filters=[{"Name": "state", "Values": ["active"]}]
            )

            for ri in response.get("ReservedInstances", []):
                self.upsert_resource(
                    service_name="ReservedInstances",
                    resource_type="EC2_RI",
                    resource_id=ri["ReservedInstancesId"],
                    region=region,
                    state=ri.get("State"),
                    tags={},
                    resource_metadata={
                        "instance_type": ri.get("InstanceType"),
                        "instance_count": ri.get("InstanceCount"),
                        "scope": ri.get("Scope"),
                        "offering_type": ri.get("OfferingType"),
                        "duration_seconds": ri.get("Duration"),
                        "fixed_price": str(ri.get("FixedPrice")),
                        "usage_price": str(ri.get("UsagePrice")),
                    }
                )

        except Exception:
            logger.exception(f"Reserved Instances scan failed | region={region}")
            raise
