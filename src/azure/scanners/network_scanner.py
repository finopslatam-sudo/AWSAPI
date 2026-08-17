import logging

from azure.mgmt.network import NetworkManagementClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class NetworkScanner(AzureBaseScanner):
    """Handles Azure Virtual Network (VNet), Load Balancer y Application Gateway.

    Los tres recursos viven bajo el mismo namespace de management
    (Microsoft.Network) y se consultan con el mismo cliente
    (NetworkManagementClient), así que comparten scanner igual que
    SQL Server/Database comparten uno solo.
    """

    # ------------------------------------------------------------------
    # VIRTUAL NETWORK
    # ------------------------------------------------------------------
    def scan_virtual_networks(self):
        try:
            network_client = NetworkManagementClient(self.credential, self.subscription_id)

            for vnet in network_client.virtual_networks.list_all():
                resource_group = vnet.id.split("/")[4]

                address_prefixes = (
                    vnet.address_space.address_prefixes if vnet.address_space else []
                )
                subnets = vnet.subnets or []

                self.upsert_resource(
                    service_name="VirtualNetwork",
                    resource_type="VirtualNetwork",
                    resource_id=vnet.id,
                    region=vnet.location,
                    state=vnet.provisioning_state,
                    tags=vnet.tags or {},
                    resource_metadata={
                        "name": vnet.name,
                        "resource_group": resource_group,
                        "address_prefixes": address_prefixes,
                        "subnet_count": len(subnets),
                        "ddos_protection_enabled": bool(vnet.enable_ddos_protection),
                    }
                )

        except Exception:
            logger.exception(f"Azure VNet scan failed | subscription={self.subscription_id}")
            raise

    # ------------------------------------------------------------------
    # LOAD BALANCER
    # ------------------------------------------------------------------
    def scan_load_balancers(self):
        try:
            network_client = NetworkManagementClient(self.credential, self.subscription_id)

            for lb in network_client.load_balancers.list_all():
                resource_group = lb.id.split("/")[4]

                backend_pools = lb.backend_address_pools or []
                total_backend_addresses = sum(
                    len(pool.load_balancer_backend_addresses or []) + len(pool.backend_ip_configurations or [])
                    for pool in backend_pools
                )

                self.upsert_resource(
                    service_name="LoadBalancer",
                    resource_type="LoadBalancer",
                    resource_id=lb.id,
                    region=lb.location,
                    state=lb.provisioning_state,
                    tags=lb.tags or {},
                    resource_metadata={
                        "name": lb.name,
                        "resource_group": resource_group,
                        "sku_name": lb.sku.name if lb.sku else None,
                        "backend_pool_count": len(backend_pools),
                        "total_backend_addresses": total_backend_addresses,
                    }
                )

        except Exception:
            logger.exception(f"Azure Load Balancer scan failed | subscription={self.subscription_id}")
            raise

    # ------------------------------------------------------------------
    # APPLICATION GATEWAY
    # ------------------------------------------------------------------
    def scan_application_gateways(self):
        try:
            network_client = NetworkManagementClient(self.credential, self.subscription_id)

            for gw in network_client.application_gateways.list_all():
                resource_group = gw.id.split("/")[4]

                backend_pools = gw.backend_address_pools or []
                total_backend_addresses = sum(
                    len(pool.backend_addresses or []) for pool in backend_pools
                )

                self.upsert_resource(
                    service_name="ApplicationGateway",
                    resource_type="ApplicationGateway",
                    resource_id=gw.id,
                    region=gw.location,
                    state=gw.operational_state or gw.provisioning_state,
                    tags=gw.tags or {},
                    resource_metadata={
                        "name": gw.name,
                        "resource_group": resource_group,
                        "sku_name": gw.sku.name if gw.sku else None,
                        "sku_tier": gw.sku.tier if gw.sku else None,
                        "autoscale_enabled": gw.autoscale_configuration is not None,
                        "backend_pool_count": len(backend_pools),
                        "total_backend_addresses": total_backend_addresses,
                    }
                )

        except Exception:
            logger.exception(f"Azure Application Gateway scan failed | subscription={self.subscription_id}")
            raise
