import boto3
import os


class STSService:

    @staticmethod
    def assume_role(role_arn: str, external_id: str, session_name: str = "finops-session"):
        """
        Asume un role en cuenta cliente usando ExternalId
        """

        sts_client = boto3.client(
            "sts",
            aws_access_key_id=os.getenv("FINOPS_AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("FINOPS_AWS_SECRET_ACCESS_KEY"),
            region_name="us-east-1"
        )

        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName=session_name,
            ExternalId=external_id
        )

        credentials = response["Credentials"]
        return credentials
