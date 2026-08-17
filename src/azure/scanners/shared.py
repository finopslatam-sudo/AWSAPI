"""
shared.py — AzureBaseScanner.

Equivalente a src/aws/scanners/shared.py (BaseScanner), pero con el
modelo de auth de Azure: Service Principal (ClientSecretCredential)
contra una Subscription, en vez de STS AssumeRole con ExternalId.

No hereda de BaseScanner (AWS) a propósito: comparten la misma *forma*
(upsert_resource idempotente), pero el bootstrap de credenciales es
fundamentalmente distinto entre boto3 y el SDK de Azure, así que forzar
una clase base común no aportaría reutilización real, solo acoplamiento
artificial entre dos SDKs que no se parecen.
"""

import logging
from datetime import datetime

from azure.identity import ClientSecretCredential
from sqlalchemy.dialects.postgresql import insert

from src.models.database import db
from src.models.azure_account import AzureAccount
from src.models.azure_resource_inventory import AzureResourceInventory


logger = logging.getLogger(__name__)


class AzureBaseScanner:
    """
    Holds Azure credentials + subscription_id y el helper compartido
    upsert_resource, usado por todos los scanners de servicios Azure.
    """

    def __init__(self, client_id, azure_account_id):
        self.client_id = client_id
        self.azure_account_id = azure_account_id

        azure_account = AzureAccount.query.get(azure_account_id)
        if not azure_account:
            raise Exception("Azure account not found")

        self.subscription_id = azure_account.subscription_id

        self.credential = ClientSecretCredential(
            tenant_id=azure_account.tenant_id,
            client_id=azure_account.app_client_id,
            client_secret=azure_account.client_secret,
        )

    # ------------------------------------------------------------------
    def upsert_resource(
        self,
        service_name,
        resource_type,
        resource_id,
        region,
        state=None,
        tags=None,
        resource_metadata=None
    ):
        now = datetime.utcnow()

        stmt = insert(AzureResourceInventory).values(
            client_id=self.client_id,
            azure_account_id=self.azure_account_id,
            service_name=service_name,
            resource_type=resource_type,
            resource_id=resource_id,
            region=region,
            state=state,
            tags=tags or {},
            resource_metadata=resource_metadata or {},
            detected_at=now,
            last_seen_at=now,
            is_active=True,
            created_at=now,
            updated_at=now
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["client_id", "resource_id"],
            set_={
                "service_name": service_name,
                "resource_type": resource_type,
                "region": region,
                "state": state,
                "tags": tags or {},
                "resource_metadata": resource_metadata or {},
                "last_seen_at": now,
                "is_active": True,
                "updated_at": now
            }
        )

        try:
            db.session.execute(stmt)
        except Exception:
            logger.exception(
                f"Azure inventory upsert failed | resource={resource_id}"
            )
            db.session.rollback()
            raise
