"""
inventory_scanner.py — orquestador de inventario Azure.

Equivalente a src/aws/inventory_scanner.py. Todavía NO está conectado a
ninguna ruta ni servicio — se activará cuando se implemente el flujo
real de conexión de cuenta Azure (fuera de alcance de esta etapa).

Servicios cubiertos hoy:
  - compute_scanner.py : Azure Virtual Machines
  - storage_scanner.py : Azure Storage Accounts
  - sql_scanner.py     : Azure SQL Database (servers + databases)
  - postgresql_scanner.py : Azure Database for PostgreSQL (Flexible Server)
  - mysql_scanner.py   : Azure Database for MySQL (Flexible Server)
  - aks_scanner.py     : Azure Kubernetes Service (AKS)
  - app_service_scanner.py : Azure App Service (Web Apps)
  - functions_scanner.py : Azure Functions
  - container_instance_scanner.py : Azure Container Instances (ACI)
  - container_registry_scanner.py : Azure Container Registry (ACR)
  - network_scanner.py : Azure Virtual Network + Load Balancer + Application
                         Gateway + Public IP + NAT Gateway + Azure Firewall
  - keyvault_scanner.py : Azure Key Vault
  - monitor_scanner.py : Azure Monitor (Log Analytics Workspaces)
  - cosmosdb_scanner.py : Azure Cosmos DB
  - cdn_scanner.py : Azure CDN / Front Door
  - dns_scanner.py : Azure DNS
  - servicebus_scanner.py : Azure Service Bus
  - snapshot_scanner.py : Azure Managed Disk Snapshots
"""

import logging
from datetime import datetime

from src.models.database import db
from src.models.azure_resource_inventory import AzureResourceInventory

from src.azure.scanners.compute_scanner import ComputeScanner
from src.azure.scanners.storage_scanner import StorageScanner
from src.azure.scanners.sql_scanner import SQLScanner
from src.azure.scanners.postgresql_scanner import PostgreSQLScanner
from src.azure.scanners.mysql_scanner import MySQLScanner
from src.azure.scanners.aks_scanner import AKSScanner
from src.azure.scanners.app_service_scanner import AppServiceScanner
from src.azure.scanners.functions_scanner import FunctionsScanner
from src.azure.scanners.container_instance_scanner import ContainerInstanceScanner
from src.azure.scanners.container_registry_scanner import ContainerRegistryScanner
from src.azure.scanners.network_scanner import NetworkScanner
from src.azure.scanners.keyvault_scanner import KeyVaultScanner
from src.azure.scanners.monitor_scanner import MonitorScanner
from src.azure.scanners.cosmosdb_scanner import CosmosDBScanner
from src.azure.scanners.cdn_scanner import CDNScanner
from src.azure.scanners.dns_scanner import DNSScanner
from src.azure.scanners.servicebus_scanner import ServiceBusScanner
from src.azure.scanners.snapshot_scanner import SnapshotScanner


logger = logging.getLogger(__name__)


class AzureInventoryScanner(
    ComputeScanner, StorageScanner, SQLScanner, PostgreSQLScanner, MySQLScanner, AKSScanner,
    AppServiceScanner, FunctionsScanner, ContainerInstanceScanner, ContainerRegistryScanner,
    NetworkScanner, KeyVaultScanner, MonitorScanner, CosmosDBScanner,
    CDNScanner, DNSScanner, ServiceBusScanner, SnapshotScanner,
):
    """
    Compone todos los scanners de servicios Azure y expone `run()`.

    A diferencia de InventoryScanner (AWS), Azure no requiere iterar
    por región: cada API de management es a nivel de suscripción y
    cada recurso reporta su propia `location` en la respuesta.
    """

    def run(self):
        logger.info(f"Azure inventory started | client_id={self.client_id}")
        now = datetime.utcnow()

        services = [
            ("VirtualMachines", self.scan_virtual_machines),
            ("StorageAccounts", self.scan_storage_accounts),
            ("SQLDatabase", self.scan_sql_databases),
            ("PostgreSQL", self.scan_postgresql_servers),
            ("MySQL", self.scan_mysql_servers),
            ("AKS", self.scan_aks_clusters),
            ("AppService", self.scan_app_services),
            ("Functions", self.scan_functions),
            ("ContainerInstances", self.scan_container_instances),
            ("ContainerRegistry", self.scan_container_registries),
            ("VirtualNetwork", self.scan_virtual_networks),
            ("LoadBalancer", self.scan_load_balancers),
            ("ApplicationGateway", self.scan_application_gateways),
            ("KeyVault", self.scan_key_vaults),
            ("Monitor", self.scan_log_analytics_workspaces),
            ("CosmosDB", self.scan_cosmosdb_accounts),
            ("ManagedDisks", self.scan_managed_disks),
            ("PublicIP", self.scan_public_ips),
            ("NATGateway", self.scan_nat_gateways),
            ("Firewall", self.scan_firewalls),
            ("CDN", self.scan_cdn_profiles),
            ("DNS", self.scan_dns_zones),
            ("ServiceBus", self.scan_namespaces),
            ("Snapshots", self.scan_snapshots),
        ]

        for service_name, service_method in services:
            try:
                service_method()
            except Exception:
                logger.exception(
                    f"{service_name} scan failed | client_id={self.client_id}"
                )

        db.session.commit()
        logger.info("Azure inventory completed")

        # Marca como inactivos los recursos no vistos en este scan
        AzureResourceInventory.query.filter(
            AzureResourceInventory.client_id == self.client_id,
            AzureResourceInventory.azure_account_id == self.azure_account_id,
            AzureResourceInventory.last_seen_at < now
        ).update({
            "is_active": False,
            "updated_at": now
        })

        db.session.commit()
