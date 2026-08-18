"""
finding_engine.py — orquestador de reglas de findings GCP.

Equivalente a src/aws/finding_engine/finding_engine.py y
src/azure/finding_engine/finding_engine.py. Todavía NO está conectado a
ninguna ruta — se activará junto con GCPInventoryScanner cuando exista
el flujo real de conexión de cuenta GCP.
"""

from src.gcp.finding_engine.compute_rules import ComputeRules
from src.gcp.finding_engine.disk_rules import DiskRules
from src.gcp.finding_engine.staticip_rules import StaticIPRules
from src.gcp.finding_engine.vpc_rules import VPCRules
from src.gcp.finding_engine.firewall_rules import FirewallRules
from src.gcp.finding_engine.load_balancer_rules import LoadBalancerRules
from src.gcp.finding_engine.nat_gateway_rules import NATGatewayRules
from src.gcp.finding_engine.storage_rules import StorageRules
from src.gcp.finding_engine.sql_rules import SQLRules
from src.gcp.finding_engine.gke_rules import GKERules
from src.gcp.finding_engine.run_rules import CloudRunRules
from src.gcp.finding_engine.functions_rules import FunctionsRules
from src.gcp.finding_engine.artifact_registry_rules import ArtifactRegistryRules
from src.gcp.finding_engine.pubsub_rules import PubSubRules
from src.gcp.finding_engine.redis_rules import RedisRules
from src.gcp.finding_engine.firestore_rules import FirestoreRules
from src.gcp.finding_engine.dns_rules import DNSRules
from src.gcp.finding_engine.filestore_rules import FilestoreRules
from src.gcp.finding_engine.kms_rules import KMSRules
from src.gcp.finding_engine.bigquery_rules import BigQueryRules
from src.gcp.finding_engine.cdn_rules import CDNRules
from src.gcp.finding_engine.logging_rules import LoggingRules
from src.gcp.finding_engine.snapshot_rules import SnapshotRules
from src.models.database import db


class GCPFindingEngine:

    @staticmethod
    def run(client_id: int):

        total_findings = 0

        try:
            total_findings += ComputeRules.run_all(client_id)
            total_findings += DiskRules.run_all(client_id)
            total_findings += StaticIPRules.run_all(client_id)
            total_findings += VPCRules.run_all(client_id)
            total_findings += FirewallRules.run_all(client_id)
            total_findings += LoadBalancerRules.run_all(client_id)
            total_findings += NATGatewayRules.run_all(client_id)
            total_findings += StorageRules.run_all(client_id)
            total_findings += SQLRules.run_all(client_id)
            total_findings += GKERules.run_all(client_id)
            total_findings += CloudRunRules.run_all(client_id)
            total_findings += FunctionsRules.run_all(client_id)
            total_findings += ArtifactRegistryRules.run_all(client_id)
            total_findings += PubSubRules.run_all(client_id)
            total_findings += RedisRules.run_all(client_id)
            total_findings += FirestoreRules.run_all(client_id)
            total_findings += DNSRules.run_all(client_id)
            total_findings += FilestoreRules.run_all(client_id)
            total_findings += KMSRules.run_all(client_id)
            total_findings += BigQueryRules.run_all(client_id)
            total_findings += CDNRules.run_all(client_id)
            total_findings += LoggingRules.run_all(client_id)
            total_findings += SnapshotRules.run_all(client_id)

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(f"[GCP FINDING ENGINE TRANSACTION ERROR]: {str(e)}")
            return 0

        return total_findings
