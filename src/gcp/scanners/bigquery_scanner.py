import logging

from src.gcp.scanners.shared import GCPBaseScanner


logger = logging.getLogger(__name__)


class BigQueryScanner(GCPBaseScanner):
    """Handles BigQuery datasets."""

    def scan_datasets(self):
        try:
            bigquery = self._client("bigquery", "v2")

            for page in self._paginate(
                bigquery.datasets(), "list", projectId=self.project_id
            ):
                for dataset in page.get("datasets", []):
                    dataset_ref = dataset.get("datasetReference") or {}
                    dataset_id = dataset_ref.get("datasetId")

                    detail = bigquery.datasets().get(
                        projectId=self.project_id, datasetId=dataset_id
                    ).execute()

                    self.upsert_resource(
                        service_name="BigQuery",
                        resource_type="Dataset",
                        resource_id=dataset.get("id", f"{self.project_id}:{dataset_id}"),
                        region=dataset.get("location"),
                        state=None,
                        tags=detail.get("labels") or {},
                        resource_metadata={
                            "dataset_id": dataset_id,
                            "default_table_expiration_ms": detail.get("defaultTableExpirationMs"),
                            "default_partition_expiration_ms": detail.get("defaultPartitionExpirationMs"),
                        }
                    )

        except Exception:
            logger.exception(f"GCP BigQuery scan failed | project={self.project_id}")
            raise
