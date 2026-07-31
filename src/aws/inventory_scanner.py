"""
inventory_scanner.py — thin orchestrator.

All service-specific scanning logic lives in src/aws/scanners/:
  - ec2_scanner.py          : EC2, EBS, Elastic IPs, EBS Snapshots, NAT Gateways, Reserved Instances
  - rds_scanner.py          : RDS, RDS Snapshots, Aurora, Redshift, DynamoDB
  - lambda_scanner.py       : Lambda, CloudWatch Logs, ECS, EKS
  - storage_scanner.py      : S3, Savings Plans
  - elb_scanner.py          : ALB/NLB, Classic ELB
  - elasticache_scanner.py  : ElastiCache
  - cloudfront_scanner.py   : CloudFront, Route53 (global)
  - sagemaker_scanner.py    : SageMaker Endpoints, Notebook Instances
  - messaging_scanner.py    : SNS, SQS
  - kinesis_scanner.py      : Kinesis Data Streams
  - opensearch_scanner.py   : OpenSearch
  - shared.py               : BaseScanner (session bootstrap + upsert_resource)
"""

import logging
from datetime import datetime

from src.models.database import db
from src.models.aws_resource_inventory import AWSResourceInventory

from src.aws.scanners.ec2_scanner import EC2Scanner
from src.aws.scanners.rds_scanner import RDSScanner
from src.aws.scanners.lambda_scanner import LambdaScanner
from src.aws.scanners.storage_scanner import StorageScanner
from src.aws.scanners.elb_scanner import ELBScanner
from src.aws.scanners.elasticache_scanner import ElastiCacheScanner
from src.aws.scanners.cloudfront_scanner import CloudFrontScanner
from src.aws.scanners.sagemaker_scanner import SageMakerScanner
from src.aws.scanners.messaging_scanner import MessagingScanner
from src.aws.scanners.kinesis_scanner import KinesisScanner
from src.aws.scanners.opensearch_scanner import OpenSearchScanner


logger = logging.getLogger(__name__)


class InventoryScanner(
    EC2Scanner, RDSScanner, LambdaScanner, StorageScanner,
    ELBScanner, ElastiCacheScanner, CloudFrontScanner, SageMakerScanner,
    MessagingScanner, KinesisScanner, OpenSearchScanner,
):
    """
    Composes all service scanners into a single class and exposes
    the public `run()` entry-point.

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
                ("ElasticIP",        self.scan_elastic_ips),
                ("EBSSnapshot",      self.scan_ebs_snapshots),
                ("RDSSnapshot",      self.scan_rds_snapshots),
                ("Aurora",           self.scan_aurora_clusters),
                ("ELB",              self.scan_load_balancers),
                ("ClassicELB",       self.scan_classic_load_balancers),
                ("ElastiCache",      self.scan_elasticache),
                ("SageMakerEndpoint", self.scan_sagemaker_endpoints),
                ("SageMakerNotebook", self.scan_sagemaker_notebooks),
                ("SNS",              self.scan_sns),
                ("SQS",              self.scan_sqs),
                ("Kinesis",          self.scan_kinesis),
                ("OpenSearch",       self.scan_opensearch),
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
            ("CloudFront",   self.scan_cloudfront,   []),
            ("Route53",      self.scan_route53,      []),
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
