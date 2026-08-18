import logging

from azure.mgmt.servicebus import ServiceBusManagementClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class ServiceBusScanner(AzureBaseScanner):
    """Handles Azure Service Bus namespaces (equivalente a SNS/SQS en
    AWS — gap real detectado en la comparativa multi-cloud)."""

    def scan_namespaces(self):
        try:
            sb_client = ServiceBusManagementClient(self.credential, self.subscription_id)

            for namespace in sb_client.namespaces.list():
                resource_group = namespace.id.split("/")[4]

                queues = list(
                    sb_client.queues.list_by_namespace(resource_group, namespace.name)
                )
                topics = list(
                    sb_client.topics.list_by_namespace(resource_group, namespace.name)
                )

                self.upsert_resource(
                    service_name="ServiceBus",
                    resource_type="Namespace",
                    resource_id=namespace.id,
                    region=namespace.location,
                    state=getattr(namespace, "status", None),
                    tags=namespace.tags or {},
                    resource_metadata={
                        "name": namespace.name,
                        "resource_group": resource_group,
                        "sku_name": namespace.sku.name if namespace.sku else None,
                        "minimum_tls_version": getattr(namespace, "minimum_tls_version", None),
                        "queue_count": len(queues),
                        "topic_count": len(topics),
                    }
                )

        except Exception:
            logger.exception(f"Azure Service Bus scan failed | subscription={self.subscription_id}")
            raise
