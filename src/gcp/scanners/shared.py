"""
shared.py — GCPBaseScanner.

Equivalente a src/azure/scanners/shared.py (AzureBaseScanner) y a
src/aws/scanners/shared.py (BaseScanner), pero con el modelo de auth de
GCP: Service Account key (JSON) contra un Project, en vez de Service
Principal (Azure) o STS AssumeRole (AWS).

Decisión de SDK: en vez de fijar ~15 paquetes `google-cloud-*` (uno por
servicio, cada uno con su propio ciclo de versiones), se usa un único
paquete — `google-api-python-client` (googleapiclient.discovery) — que
construye clientes REST genéricos para cualquier API de Google Cloud
(compute, storage, sqladmin, container, run, cloudfunctions, bigquery,
dns, redis, firestore, artifactregistry, pubsub, cloudkms, file) a
partir de su nombre y versión. Es el equivalente más cercano al patrón
boto3 (un solo SDK, muchos servicios) ya usado para AWS.
"""

import logging
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from sqlalchemy.dialects.postgresql import insert

from src.models.database import db
from src.models.gcp_account import GCPAccount
from src.models.gcp_resource_inventory import GCPResourceInventory


logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/cloud-platform.read-only"]


class GCPBaseScanner:
    """
    Holds GCP credentials + project_id y el helper compartido
    upsert_resource, usado por todos los scanners de servicios GCP.
    """

    def __init__(self, client_id, gcp_account_id):
        self.client_id = client_id
        self.gcp_account_id = gcp_account_id

        gcp_account = GCPAccount.query.get(gcp_account_id)
        if not gcp_account:
            raise Exception("GCP account not found")

        self.project_id = gcp_account.project_id

        self.credentials = service_account.Credentials.from_service_account_info(
            gcp_account.service_account_key, scopes=SCOPES
        )

    def _client(self, api_name, api_version):
        """Construye un cliente REST para una API de Google Cloud dada."""
        return build(
            api_name,
            api_version,
            credentials=self.credentials,
            cache_discovery=False,
        )

    @staticmethod
    def _paginate(collection, list_method_name, **params):
        """
        Sigue nextPageToken hasta agotar resultados. Sirve tanto para
        list() como para aggregatedList() de la API de Compute — ambas
        exponen el método `<list_method_name>_next` generado por
        discovery para paginación.
        """
        method = getattr(collection, list_method_name)
        request = method(**params)
        responses = []

        while request is not None:
            response = request.execute()
            responses.append(response)

            next_method = getattr(collection, f"{list_method_name}_next", None)
            request = (
                next_method(previous_request=request, previous_response=response)
                if next_method else None
            )

        return responses

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

        stmt = insert(GCPResourceInventory).values(
            client_id=self.client_id,
            gcp_account_id=self.gcp_account_id,
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
                f"GCP inventory upsert failed | resource={resource_id}"
            )
            db.session.rollback()
            raise
