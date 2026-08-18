import json
import logging

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.models.gcp_account import GCPAccount
from src.models.database import db
from src.auth.plan_permissions import get_plan_limit

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/cloud-platform.read-only"]


class GCPConnectionService:
    """
    Equivalente a AWSConnectionService/AzureConnectionService, pero con
    el modelo de auth de GCP: el cliente crea manualmente una Service
    Account en GCP Console y nos entrega el JSON key completo — no hay
    flujo tipo CloudFormation/ExternalId (AWS) ni Service Principal
    separado por campos (Azure).
    """

    @staticmethod
    def check_account_limit(client_id):
        limit = get_plan_limit(client_id, "gcp_accounts")
        current_accounts = GCPAccount.query.filter_by(
            client_id=client_id, is_active=True
        ).count()
        if current_accounts >= limit:
            raise RuntimeError(
                f"GCP account limit reached for your plan ({limit})."
            )

    @staticmethod
    def validate_and_save_account(client_id, service_account_key_raw):
        if not service_account_key_raw:
            raise RuntimeError("Missing required GCP connection data")

        try:
            key_info = (
                json.loads(service_account_key_raw)
                if isinstance(service_account_key_raw, str)
                else service_account_key_raw
            )
        except (TypeError, ValueError):
            raise RuntimeError("Invalid service account key JSON")

        project_id = key_info.get("project_id")
        client_email = key_info.get("client_email")

        if not project_id or not client_email:
            raise RuntimeError(
                "Service account key missing project_id/client_email"
            )

        GCPConnectionService.check_account_limit(client_id)

        logger.info(
            "Attempting GCP Service Account auth for project_id=%s", project_id
        )

        try:
            credentials = service_account.Credentials.from_service_account_info(
                key_info, scopes=SCOPES
            )
            resource_manager = build(
                "cloudresourcemanager", "v1",
                credentials=credentials, cache_discovery=False
            )
            project = resource_manager.projects().get(
                projectId=project_id
            ).execute()
        except HttpError as e:
            raise RuntimeError(f"Unable to verify GCP project: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"GCP connection error: {str(e)}")

        project_name = project.get("name") or project_id
        service_account_key_json = json.dumps(key_info)

        existing = GCPAccount.query.filter_by(
            client_id=client_id, project_id=project_id
        ).first()

        if existing:
            logger.info("Updating existing GCP account: %s", project_name)
            existing.project_name = project_name
            existing.service_account_email = client_email
            existing.service_account_key = service_account_key_json
            existing.is_active = True
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise RuntimeError("Database error while updating GCP account")
            return existing.id

        gcp_account = GCPAccount(
            client_id=client_id,
            project_id=project_id,
            project_name=project_name,
            service_account_email=client_email,
            service_account_key=service_account_key_json,
            is_active=True,
        )
        try:
            db.session.add(gcp_account)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise RuntimeError("Database error while saving GCP account")

        return gcp_account.id
