import logging
from datetime import datetime

import boto3
from sqlalchemy.dialects.postgresql import insert

from src.models.database import db
from src.models.aws_account import AWSAccount
from src.models.aws_resource_inventory import AWSResourceInventory
from src.aws.sts_service import STSService


logger = logging.getLogger(__name__)


class BaseScanner:
    """
    Holds the boto3 session and the shared helpers (upsert_resource,
    get_enabled_regions) used by every service-specific scanner.
    """

    def __init__(self, client_id, aws_account_id):
        self.client_id = client_id
        self.aws_account_id = aws_account_id

        aws_account = AWSAccount.query.get(aws_account_id)
        if not aws_account:
            raise Exception("AWS account not found")

        sts_service = STSService()

        credentials = sts_service.assume_role(
            role_arn=aws_account.role_arn,
            external_id=aws_account.external_id,
            session_name="finops-inventory"
        )

        self.aws_session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

    # ------------------------------------------------------------------
    def get_enabled_regions(self):
        ec2 = self.aws_session.client("ec2", region_name="us-east-1")
        response = ec2.describe_regions(AllRegions=False)
        return [r["RegionName"] for r in response["Regions"]]

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

        # Normalise region — strip trailing AZ letter (e.g. "us-east-1a" -> "us-east-1")
        if region and len(region) > 9 and region[-1].isalpha():
            region = region[:-1]

        stmt = insert(AWSResourceInventory).values(
            client_id=self.client_id,
            aws_account_id=self.aws_account_id,
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
                f"Inventory upsert failed | resource={resource_id}"
            )
            db.session.rollback()
            raise
