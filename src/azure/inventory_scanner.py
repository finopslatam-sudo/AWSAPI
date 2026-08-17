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
"""

import logging
from datetime import datetime

from src.models.database import db
from src.models.azure_resource_inventory import AzureResourceInventory

from src.azure.scanners.compute_scanner import ComputeScanner
from src.azure.scanners.storage_scanner import StorageScanner
from src.azure.scanners.sql_scanner import SQLScanner
from src.azure.scanners.postgresql_scanner import PostgreSQLScanner


logger = logging.getLogger(__name__)


class AzureInventoryScanner(ComputeScanner, StorageScanner, SQLScanner, PostgreSQLScanner):
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
