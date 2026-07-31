import logging

from src.aws.scanners.shared import BaseScanner


logger = logging.getLogger(__name__)


class OpenSearchScanner(BaseScanner):
    """Handles OpenSearch/Elasticsearch domains."""

    def scan_opensearch(self, region):
        try:
            opensearch = self.aws_session.client("opensearch", region_name=region)
            domain_names = [
                d["DomainName"]
                for d in opensearch.list_domain_names().get("DomainNames", [])
            ]

            if not domain_names:
                return

            domains = opensearch.describe_domains(
                DomainNames=domain_names
            ).get("DomainStatusList", [])

            for domain in domains:
                cluster_config = domain.get("ClusterConfig", {})

                self.upsert_resource(
                    service_name="OpenSearch",
                    resource_type="Domain",
                    resource_id=domain["ARN"],
                    region=region,
                    state="active" if not domain.get("Processing") else "processing",
                    tags={},
                    resource_metadata={
                        "name": domain.get("DomainName"),
                        "instance_type": cluster_config.get("InstanceType"),
                        "instance_count": cluster_config.get("InstanceCount"),
                        "dedicated_master_enabled": cluster_config.get("DedicatedMasterEnabled"),
                        "encryption_at_rest": domain.get("EncryptionAtRestOptions", {}).get("Enabled"),
                    }
                )

        except Exception:
            logger.exception(f"OpenSearch scan failed | region={region}")
            raise
