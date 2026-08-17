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

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(f"[AZURE FINDING ENGINE TRANSACTION ERROR]: {str(e)}")
            return 0

        return total_findings
