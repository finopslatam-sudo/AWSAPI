"""
finding_engine.py — orquestador de reglas de findings Azure.

Equivalente a src/aws/finding_engine/finding_engine.py. Todavía NO está
conectado a ninguna ruta — se activará junto con AzureInventoryScanner
cuando exista el flujo real de conexión de cuenta Azure.
"""

from src.azure.finding_engine.vm_rules import VMRules
from src.azure.finding_engine.storage_rules import StorageRules
from src.azure.finding_engine.sql_rules import SQLRules
from src.azure.finding_engine.postgresql_rules import PostgreSQLRules
from src.azure.finding_engine.mysql_rules import MySQLRules
from src.azure.finding_engine.aks_rules import AKSRules
from src.azure.finding_engine.app_service_rules import AppServiceRules
from src.azure.finding_engine.functions_rules import FunctionsRules
from src.azure.finding_engine.container_instance_rules import ContainerInstanceRules
from src.azure.finding_engine.container_registry_rules import ContainerRegistryRules
from src.azure.finding_engine.vnet_rules import VNetRules
from src.azure.finding_engine.load_balancer_rules import LoadBalancerRules
from src.azure.finding_engine.app_gateway_rules import AppGatewayRules
from src.azure.finding_engine.keyvault_rules import KeyVaultRules
from src.azure.finding_engine.monitor_rules import MonitorRules
from src.azure.finding_engine.cosmosdb_rules import CosmosDBRules
from src.azure.finding_engine.managed_disk_rules import ManagedDiskRules
from src.azure.finding_engine.public_ip_rules import PublicIPRules
from src.azure.finding_engine.nat_gateway_rules import NATGatewayRules
from src.azure.finding_engine.firewall_rules import FirewallRules
from src.azure.finding_engine.cdn_rules import CDNRules
from src.azure.finding_engine.dns_rules import DNSRules
from src.azure.finding_engine.servicebus_rules import ServiceBusRules
from src.models.database import db


class AzureFindingEngine:

    @staticmethod
    def run(client_id: int):

        total_findings = 0

        try:
            total_findings += VMRules.run_all(client_id)
            total_findings += StorageRules.run_all(client_id)
            total_findings += SQLRules.run_all(client_id)
            total_findings += PostgreSQLRules.run_all(client_id)
            total_findings += MySQLRules.run_all(client_id)
            total_findings += AKSRules.run_all(client_id)
            total_findings += AppServiceRules.run_all(client_id)
            total_findings += FunctionsRules.run_all(client_id)
            total_findings += ContainerInstanceRules.run_all(client_id)
            total_findings += ContainerRegistryRules.run_all(client_id)
            total_findings += VNetRules.run_all(client_id)
            total_findings += LoadBalancerRules.run_all(client_id)
            total_findings += AppGatewayRules.run_all(client_id)
            total_findings += KeyVaultRules.run_all(client_id)
            total_findings += MonitorRules.run_all(client_id)
            total_findings += CosmosDBRules.run_all(client_id)
            total_findings += ManagedDiskRules.run_all(client_id)
            total_findings += PublicIPRules.run_all(client_id)
            total_findings += NATGatewayRules.run_all(client_id)
            total_findings += FirewallRules.run_all(client_id)
            total_findings += CDNRules.run_all(client_id)
            total_findings += DNSRules.run_all(client_id)
            total_findings += ServiceBusRules.run_all(client_id)

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(f"[AZURE FINDING ENGINE TRANSACTION ERROR]: {str(e)}")
            return 0

        return total_findings
