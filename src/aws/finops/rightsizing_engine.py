import boto3
from datetime import datetime, timedelta
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding
from src.models.database import db
from src.aws.sts_service import STSService
from src.models.aws_account import AWSAccount


class RightsizingEngine:

    @staticmethod
    def run(client_id):

        aws_account = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        ).first()

        if not aws_account:
            return 0

        sts = STSService()

        credentials = sts.assume_role(
            role_arn=aws_account.role_arn,
            external_id=aws_account.external_id,
            session_name="finops-rightsizing"
        )

        session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

        total = 0

        total += RightsizingEngine.evaluate_ec2(session, client_id)
        total += RightsizingEngine.evaluate_rds(session, client_id)

        return total
    
    @staticmethod
    def evaluate_ec2(session, client_id):

        count = 0

        instances = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="EC2",
            is_active=True
        ).all()

        for instance in instances:

            if instance.state != "running":
                continue

            region = instance.region
            instance_id = instance.resource_id

            cloudwatch = session.client(
                "cloudwatch",
                region_name=region
            )

            end = datetime.utcnow()
            start = end - timedelta(days=7)

            metrics = cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[
                    {"Name": "InstanceId", "Value": instance_id}
                ],
                StartTime=start,
                EndTime=end,
                Period=86400,
                Statistics=["Average"]
            )

            datapoints = metrics.get("Datapoints", [])

            if not datapoints:
                continue

            avg_cpu = sum(
                d["Average"] for d in datapoints
            ) / len(datapoints)

            if avg_cpu < 10:

                AWSFinding.upsert_finding(
                    client_id=client_id,
                    aws_account_id=instance.aws_account_id,
                    resource_id=instance_id,
                    resource_type="EC2",
                    finding_type="EC2_UNDERUTILIZED",
                    severity="MEDIUM",
                    message=f"Average CPU last 7 days: {round(avg_cpu,2)}%",
                    estimated_monthly_savings=100.0
                )

                count += 1

        return count