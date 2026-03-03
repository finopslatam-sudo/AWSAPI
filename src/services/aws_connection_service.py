import uuid
import os
import boto3

from src.models.aws_account import AWSAccount
from src.models.database import db
from src.aws.sts_service import STSService


class AWSConnectionService:

    @staticmethod
    def generate_external_id():
        return str(uuid.uuid4())

    @staticmethod
    def build_cloudformation_url(external_id: str):

        finops_account_id = os.getenv("FINOPS_AWS_ACCOUNT_ID")

        template_url = (
            "https://finopslatam-onboarding.s3.amazonaws.com/"
            "finopslatam_role.yaml"
        )

        return (
            "https://console.aws.amazon.com/cloudformation/home"
            "?region=us-east-1#/stacks/create/review"
            f"?templateURL={template_url}"
            f"&stackName=FinOpsLatamStack"
            f"&param_ExternalId={external_id}"
            f"&param_FinOpsAccountId={finops_account_id}"
        )

    @staticmethod
    def validate_and_save_account(client_id, role_arn, external_id):

        creds = STSService.assume_role(role_arn, external_id)

        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
        )

        sts = session.client("sts")
        identity = sts.get_caller_identity()

        account_id = identity["Account"]

        aws_account = AWSAccount(
            client_id=client_id,
            account_id=account_id,
            account_name="Primary",
            role_arn=role_arn,
            external_id=external_id,
            is_active=True
        )

        db.session.add(aws_account)
        db.session.commit()

        return account_id