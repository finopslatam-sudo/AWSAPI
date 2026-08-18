import logging

from azure.identity import ClientSecretCredential
from azure.mgmt.subscription import SubscriptionClient
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError

from src.models.azure_account import AzureAccount
from src.models.database import db
from src.auth.plan_permissions import get_plan_limit

logger = logging.getLogger(__name__)


class AzureConnectionService:
    """
    Equivalente a AWSConnectionService, pero con el modelo de auth de
    Azure: el cliente crea manualmente un App Registration (Service
    Principal) en Azure Portal y nos entrega Tenant ID + App Client ID
    + Client Secret + Subscription ID directamente — no hay flujo tipo
    CloudFormation/ExternalId como en AWS.
    """

    @staticmethod
    def check_account_limit(client_id):
        limit = get_plan_limit(client_id, "azure_accounts")
        current_accounts = AzureAccount.query.filter_by(
            client_id=client_id, is_active=True
        ).count()
        if current_accounts >= limit:
            raise RuntimeError(
                f"Azure account limit reached for your plan ({limit})."
            )

    @staticmethod
    def validate_and_save_account(
        client_id, subscription_id, tenant_id, app_client_id, client_secret
    ):
        if not all([subscription_id, tenant_id, app_client_id, client_secret]):
            raise RuntimeError("Missing required Azure connection data")

        AzureConnectionService.check_account_limit(client_id)

        logger.info(
            "Attempting Azure Service Principal auth for subscription_id=%s",
            subscription_id
        )

        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=app_client_id,
            client_secret=client_secret,
        )

        try:
            subscription_client = SubscriptionClient(credential)
            subscription = subscription_client.subscriptions.get(subscription_id)
        except ClientAuthenticationError as e:
            raise RuntimeError(f"Azure authentication failed: {str(e)}")
        except HttpResponseError as e:
            raise RuntimeError(f"Unable to verify Azure subscription: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Azure connection error: {str(e)}")

        subscription_name = subscription.display_name or subscription_id

        existing = AzureAccount.query.filter_by(
            client_id=client_id, subscription_id=subscription_id
        ).first()

        if existing:
            logger.info("Updating existing Azure account: %s", subscription_name)
            existing.subscription_name = subscription_name
            existing.tenant_id = tenant_id
            existing.app_client_id = app_client_id
            existing.client_secret = client_secret
            existing.is_active = True
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise RuntimeError("Database error while updating Azure account")
            return existing.id

        azure_account = AzureAccount(
            client_id=client_id,
            subscription_id=subscription_id,
            subscription_name=subscription_name,
            tenant_id=tenant_id,
            app_client_id=app_client_id,
            client_secret=client_secret,
            is_active=True,
        )
        try:
            db.session.add(azure_account)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise RuntimeError("Database error while saving Azure account")

        return azure_account.id
