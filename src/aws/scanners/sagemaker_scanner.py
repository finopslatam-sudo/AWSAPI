import logging

from src.aws.scanners.shared import BaseScanner


logger = logging.getLogger(__name__)


class SageMakerScanner(BaseScanner):
    """Handles SageMaker endpoints (real-time inference) and notebook instances."""

    # ------------------------------------------------------------------
    # ENDPOINTS
    # ------------------------------------------------------------------
    def scan_sagemaker_endpoints(self, region):
        try:
            sagemaker = self.aws_session.client("sagemaker", region_name=region)
            paginator = sagemaker.get_paginator("list_endpoints")

            for page in paginator.paginate():
                for endpoint in page.get("Endpoints", []):
                    self.upsert_resource(
                        service_name="SageMaker",
                        resource_type="Endpoint",
                        resource_id=endpoint["EndpointArn"],
                        region=region,
                        state=endpoint.get("EndpointStatus"),
                        tags={},
                        resource_metadata={
                            "name": endpoint.get("EndpointName"),
                            "creation_time": str(endpoint.get("CreationTime")),
                        }
                    )

        except Exception:
            logger.exception(f"SageMaker endpoints scan failed | region={region}")
            raise

    # ------------------------------------------------------------------
    # NOTEBOOK INSTANCES
    # ------------------------------------------------------------------
    def scan_sagemaker_notebooks(self, region):
        try:
            sagemaker = self.aws_session.client("sagemaker", region_name=region)
            paginator = sagemaker.get_paginator("list_notebook_instances")

            for page in paginator.paginate():
                for notebook in page.get("NotebookInstances", []):
                    self.upsert_resource(
                        service_name="SageMaker",
                        resource_type="NotebookInstance",
                        resource_id=notebook["NotebookInstanceArn"],
                        region=region,
                        state=notebook.get("NotebookInstanceStatus"),
                        tags={},
                        resource_metadata={
                            "name": notebook.get("NotebookInstanceName"),
                            "instance_type": notebook.get("InstanceType"),
                        }
                    )

        except Exception:
            logger.exception(f"SageMaker notebooks scan failed | region={region}")
            raise
