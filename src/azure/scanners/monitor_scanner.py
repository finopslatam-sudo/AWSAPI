import logging

from azure.mgmt.loganalytics import LogAnalyticsManagementClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class MonitorScanner(AzureBaseScanner):
    """Handles Azure Monitor — a través de los Log Analytics Workspaces,
    el recurso concreto y facturable de Azure Monitor (equivalente a
    CloudWatch Logs en AWS)."""

    def scan_log_analytics_workspaces(self):
        try:
            monitor_client = LogAnalyticsManagementClient(self.credential, self.subscription_id)

            for workspace in monitor_client.workspaces.list():
                resource_group = workspace.id.split("/")[4]

                capping = workspace.workspace_capping
                daily_quota_gb = capping.daily_quota_gb if capping else None

                self.upsert_resource(
                    service_name="Monitor",
                    resource_type="LogAnalyticsWorkspace",
                    resource_id=workspace.id,
                    region=workspace.location,
                    state=workspace.provisioning_state,
                    tags=workspace.tags or {},
                    resource_metadata={
                        "name": workspace.name,
                        "resource_group": resource_group,
                        "sku_name": workspace.sku.name if workspace.sku else None,
                        "retention_in_days": workspace.retention_in_days,
                        "daily_quota_gb": daily_quota_gb,
                    }
                )

        except Exception:
            logger.exception(f"Azure Monitor scan failed | subscription={self.subscription_id}")
            raise
