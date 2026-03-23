"""
inventory_scanner.py — thin orchestrator.

All service-specific scanning logic lives in src/aws/scanners/:
  - ec2_scanner.py     : EC2, EBS, NAT Gateways, Reserved Instances
  - rds_scanner.py     : RDS, Redshift, DynamoDB
  - lambda_scanner.py  : Lambda, CloudWatch Logs, ECS, EKS
  - storage_scanner.py : S3, Savings Plans
  - shared.py          : BaseScanner (session bootstrap + upsert_resource)
"""

import logging
from datetime import datetime

from src.models.database import db
from src.models.aws_resource_inventory import AWSResourceInventory

from src.aws.scanners.ec2_scanner import EC2Scanner
from src.aws.scanners.rds_scanner import RDSScanner
from src.aws.scanners.lambda_scanner import LambdaScanner
from src.aws.scanners.storage_scanner import StorageScanner


logger = logging.getLogger(__name__)


class InventoryScanner(EC2Scanner, RDSScanner, LambdaScanner, StorageScanner):
    """
    Composes all service scanners into a single class and exposes
    the public `run()` entry-point.

    The MRO is:
      InventoryScanner -> EC2Scanner -> RDSScanner
                       -> LambdaScanner -> StorageScanner
                       -> BaseScanner
    All mixins inherit from BaseScanner, so __init__ and the shared
    helpers (upsert_resource, get_enabled_regions) are available
    to every method.
    """

    # ------------------------------------------------------------------
    # PUBLIC ENTRY-POINT
    # ------------------------------------------------------------------
    def run(self):
        logger.info(f"Inventory started | client_id={self.client_id}")
        now = datetime.utcnow()

        regions = self.get_enabled_regions()

        for region in regions:
            logger.info(f"Scanning region {region}")

            regional_services = [
                ("EC2",              self.scan_ec2),
                ("EBS",              self.scan_ebs),
                ("RDS",              self.scan_rds),
                ("Lambda",           self.scan_lambda),
                ("DynamoDB",         self.scan_dynamodb),
                ("CloudWatchLogs",   self.scan_cloudwatch_logs),
                ("NAT",              self.scan_nat_gateways),
                ("ECS",              self.scan_ecs),
                ("Redshift",         self.scan_redshift),
                ("EKS",              self.scan_eks),
                ("ReservedInstances", self.scan_reserved_instances),
            ]

            for service_name, service_method in regional_services:
                try:
                    service_method(region)
                except Exception:
                    logger.exception(
                        f"{service_name} scan failed | region={region} | client_id={self.client_id}"
                    )

            db.session.commit()

        # Global services
        for label, fn, args in [
            ("S3",           self.scan_s3,           []),
            ("SavingsPlans", self.scan_savings_plans, [None]),
        ]:
            try:
                fn(*args)
            except Exception:
                logger.exception(
                    f"{label} scan failed | client_id={self.client_id}"
                )

        db.session.commit()
        logger.info("Inventory completed")

        # Mark resources not seen in this scan as inactive
        AWSResourceInventory.query.filter(
            AWSResourceInventory.client_id == self.client_id,
            AWSResourceInventory.aws_account_id == self.aws_account_id,
            AWSResourceInventory.last_seen_at < now
        ).update({
            "is_active": False,
            "updated_at": now
        })

        db.session.commit()
