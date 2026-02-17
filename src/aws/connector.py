import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from typing import Dict

DEFAULT_REGION = "us-east-1"


class AWSConnector:
    def __init__(self, role_arn: str, external_id: str | None = None):
        self.role_arn = role_arn
        self.external_id = external_id
        self.session = None

    def assume_role(self):
        try:
            sts = boto3.client("sts", region_name=DEFAULT_REGION)

            assume_params = {
                "RoleArn": self.role_arn,
                "RoleSessionName": f"FinOpsLatamSession-{datetime.utcnow().timestamp()}",
            }

            if self.external_id:
                assume_params["ExternalId"] = self.external_id

            response = sts.assume_role(**assume_params)

            credentials = response["Credentials"]

            self.session = boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                region_name=DEFAULT_REGION,
            )

            return True

        except ClientError as e:
            raise Exception(f"AssumeRole failed: {str(e)}")

    def get_client(self, service_name: str):
        if not self.session:
            raise Exception("Session not initialized. Call assume_role() first.")
        return self.session.client(service_name)
