import logging

from botocore.exceptions import ClientError

from src.aws.scanners.shared import BaseScanner


logger = logging.getLogger(__name__)


class RDSScanner(BaseScanner):
    """Handles RDS instances, Redshift clusters, and DynamoDB tables."""

    # ------------------------------------------------------------------
    # RDS
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # REDSHIFT
    # ------------------------------------------------------------------
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

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in ["OptInRequired", "AccessDeniedException"]:
                logger.info(f"Redshift not enabled in region {region}")
                return
            logger.exception(f"Redshift scan failed | region={region}")
            raise

        except Exception:
            logger.exception(f"Redshift scan failed | region={region}")
            raise

    # ------------------------------------------------------------------
    # DYNAMODB
    # ------------------------------------------------------------------
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
                            "provisioned_wcu": table.get("ProvisionedThroughput", {}).get("WriteCapacityUnits"),
                            "provisioned_rcu": table.get("ProvisionedThroughput", {}).get("ReadCapacityUnits"),
                        }
                    )

        except Exception:
            logger.exception(f"DynamoDB scan failed | region={region}")
            raise
