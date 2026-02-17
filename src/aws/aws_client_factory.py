import boto3


class AWSClientFactory:

    @staticmethod
    def create_client(service_name: str, credentials: dict):
        return boto3.client(
            service_name,
            aws_access_key_id=credentials["access_key"],
            aws_secret_access_key=credentials["secret_key"],
            aws_session_token=credentials["session_token"],
            region_name="us-east-1"
        )
