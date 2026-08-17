import logging

from azure.mgmt.network import NetworkManagementClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class NetworkScanner(AzureBaseScanner):
    """Handles Azure Virtual Network (VNet), Load Balancer, Application
    Gateway, Public IP, NAT Gateway y Azure Firewall.

    Los seis recursos viven bajo el mismo namespace de management
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

    # ------------------------------------------------------------------
    # PUBLIC IP
    # ------------------------------------------------------------------
    def scan_public_ips(self):
        try:
            network_client = NetworkManagementClient(self.credential, self.subscription_id)

            for ip in network_client.public_ip_addresses.list_all():
                resource_group = ip.id.split("/")[4]

                self.upsert_resource(
                    service_name="PublicIP",
                    resource_type="PublicIPAddress",
                    resource_id=ip.id,
                    region=ip.location,
                    state="associated" if ip.ip_configuration else "unassociated",
                    tags=ip.tags or {},
                    resource_metadata={
                        "name": ip.name,
                        "resource_group": resource_group,
                        "sku_name": ip.sku.name if ip.sku else None,
                        "ip_address": ip.ip_address,
                        "allocation_method": ip.public_ip_allocation_method,
                    }
                )

        except Exception:
            logger.exception(f"Azure Public IP scan failed | subscription={self.subscription_id}")
            raise

    # ------------------------------------------------------------------
    # NAT GATEWAY
    # ------------------------------------------------------------------
    def scan_nat_gateways(self):
        try:
            network_client = NetworkManagementClient(self.credential, self.subscription_id)

            for nat in network_client.nat_gateways.list_all():
                resource_group = nat.id.split("/")[4]

                subnets = nat.subnets or []
                public_ips = nat.public_ip_addresses or []

                self.upsert_resource(
                    service_name="NATGateway",
                    resource_type="NatGateway",
                    resource_id=nat.id,
                    region=nat.location,
                    state=nat.provisioning_state,
                    tags=nat.tags or {},
                    resource_metadata={
                        "name": nat.name,
                        "resource_group": resource_group,
                        "sku_name": nat.sku.name if nat.sku else None,
                        "subnet_count": len(subnets),
                        "public_ip_count": len(public_ips),
                    }
                )

        except Exception:
            logger.exception(f"Azure NAT Gateway scan failed | subscription={self.subscription_id}")
            raise

    # ------------------------------------------------------------------
    # AZURE FIREWALL
    # ------------------------------------------------------------------
    def scan_firewalls(self):
        try:
            network_client = NetworkManagementClient(self.credential, self.subscription_id)

            for fw in network_client.azure_firewalls.list_all():
                resource_group = fw.id.split("/")[4]

                ip_configs = fw.ip_configurations or []
                hub_ip_addresses = fw.hub_ip_addresses

                self.upsert_resource(
                    service_name="Firewall",
                    resource_type="AzureFirewall",
                    resource_id=fw.id,
                    region=fw.location,
                    state=fw.provisioning_state,
                    tags=fw.tags or {},
                    resource_metadata={
                        "name": fw.name,
                        "resource_group": resource_group,
                        "sku_name": fw.sku.name if fw.sku else None,
                        "sku_tier": fw.sku.tier if fw.sku else None,
                        "ip_configuration_count": len(ip_configs),
                        "has_hub_ip": hub_ip_addresses is not None,
                    }
                )

        except Exception:
            logger.exception(f"Azure Firewall scan failed | subscription={self.subscription_id}")
            raise
