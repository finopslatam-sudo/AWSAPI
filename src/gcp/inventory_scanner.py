"""
inventory_scanner.py — orquestador de inventario GCP.

Equivalente a src/aws/inventory_scanner.py y src/azure/inventory_scanner.py.
Todavía NO está conectado a ninguna ruta ni servicio — se activará
cuando se implemente el flujo real de conexión de cuenta GCP (fuera de
alcance de esta etapa).

Servicios cubiertos hoy:
  - compute_scanner.py    : Compute Engine + Persistent Disks + Static IPs
  - network_scanner.py    : VPC Networks + Firewall Rules + Load Balancing + Cloud NAT
  - storage_scanner.py    : Cloud Storage
  - sql_scanner.py        : Cloud SQL
  - gke_scanner.py        : Google Kubernetes Engine (GKE)
  - run_scanner.py        : Cloud Run
  - functions_scanner.py  : Cloud Functions
  - bigquery_scanner.py   : BigQuery
  - kms_scanner.py        : Cloud KMS
  - artifact_registry_scanner.py : Artifact Registry
  - pubsub_scanner.py     : Pub/Sub
  - redis_scanner.py      : Memorystore (Redis)
  - firestore_scanner.py  : Firestore
  - dns_scanner.py        : Cloud DNS
  - filestore_scanner.py  : Filestore
"""

import logging
from datetime import datetime

from src.models.database import db
from src.models.gcp_resource_inventory import GCPResourceInventory

from src.gcp.scanners.compute_scanner import ComputeScanner
from src.gcp.scanners.network_scanner import NetworkScanner
from src.gcp.scanners.storage_scanner import StorageScanner
from src.gcp.scanners.sql_scanner import SQLScanner
from src.gcp.scanners.gke_scanner import GKEScanner
from src.gcp.scanners.run_scanner import RunScanner
from src.gcp.scanners.functions_scanner import FunctionsScanner
from src.gcp.scanners.bigquery_scanner import BigQueryScanner
from src.gcp.scanners.kms_scanner import KMSScanner
from src.gcp.scanners.artifact_registry_scanner import ArtifactRegistryScanner
from src.gcp.scanners.pubsub_scanner import PubSubScanner
from src.gcp.scanners.redis_scanner import RedisScanner
from src.gcp.scanners.firestore_scanner import FirestoreScanner
from src.gcp.scanners.dns_scanner import DNSScanner
from src.gcp.scanners.filestore_scanner import FilestoreScanner


logger = logging.getLogger(__name__)


class GCPInventoryScanner(
    ComputeScanner, NetworkScanner, StorageScanner, SQLScanner, GKEScanner,
    RunScanner, FunctionsScanner, BigQueryScanner, KMSScanner, ArtifactRegistryScanner,
    PubSubScanner, RedisScanner, FirestoreScanner, DNSScanner, FilestoreScanner,
):
    """
    Compone todos los scanners de servicios GCP y expone `run()`.

    Igual que Azure, cada API de GCP es a nivel de proyecto (no hace
    falta iterar por región manualmente como en AWS): la mayoría de
    métodos usan aggregatedList o parent="projects/{p}/locations/-".
    """

    def run(self):
        logger.info(f"GCP inventory started | client_id={self.client_id}")
        now = datetime.utcnow()

        services = [
            ("ComputeEngine", self.scan_instances),
            ("PersistentDisks", self.scan_disks),
            ("StaticIPs", self.scan_addresses),
            ("VPCNetworks", self.scan_networks),
            ("FirewallRules", self.scan_firewalls),
            ("LoadBalancing", self.scan_load_balancers),
            ("CloudNAT", self.scan_nat_gateways),
            ("CloudStorage", self.scan_buckets),
            ("CloudSQL", self.scan_sql_instances),
            ("GKE", self.scan_clusters),
            ("CloudRun", self.scan_services),
            ("CloudFunctions", self.scan_functions),
            ("BigQuery", self.scan_datasets),
            ("CloudKMS", self.scan_key_rings),
            ("ArtifactRegistry", self.scan_repositories),
            ("PubSub", self.scan_topics),
            ("Memorystore", self.scan_redis_instances),
            ("Firestore", self.scan_databases),
            ("CloudDNS", self.scan_managed_zones),
            ("Filestore", self.scan_filestore_instances),
        ]

        for service_name, service_method in services:
            try:
                service_method()
            except Exception:
                logger.exception(
                    f"{service_name} scan failed | client_id={self.client_id}"
                )

        db.session.commit()
        logger.info("GCP inventory completed")

        # Marca como inactivos los recursos no vistos en este scan
        GCPResourceInventory.query.filter(
            GCPResourceInventory.client_id == self.client_id,
            GCPResourceInventory.gcp_account_id == self.gcp_account_id,
            GCPResourceInventory.last_seen_at < now
        ).update({
            "is_active": False,
            "updated_at": now
        })

        db.session.commit()
