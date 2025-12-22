import boto3
import os
from botocore.config import Config

class AWSConfig:
    def __init__(self):
        self.region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        # Configuración optimizada para Free Tier
        self.config = Config(
            region_name=self.region,
            retries={'max_attempts': 3, 'mode': 'standard'},
            signature_version='v4'
        )
    
    def get_cost_explorer_client(self):
        return boto3.client('ce', config=self.config)
    
    def get_ec2_client(self):
        return boto3.client('ec2', config=self.config)
    
    def get_cloudwatch_client(self):
        return boto3.client('cloudwatch', config=self.config)