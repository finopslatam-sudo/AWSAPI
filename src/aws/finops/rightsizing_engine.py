import boto3
from datetime import datetime, timedelta
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding
from src.aws.sts_service import STSService
from src.models.aws_account import AWSAccount


class RightsizingEngine:

    @staticmethod
    def run(client_id, aws_account_id=None):

        accounts_query = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        )

        if aws_account_id is not None:
            accounts_query = accounts_query.filter_by(id=aws_account_id)

        aws_accounts = accounts_query.all()

        if not aws_accounts:
            return 0

        sts = STSService()
        total = 0

        for aws_account in aws_accounts:
            credentials = sts.assume_role(
                role_arn=aws_account.role_arn,
                external_id=aws_account.external_id,
                session_name=f"finops-rightsizing-{aws_account.id}"
            )

            session = boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
            )

            total += RightsizingEngine.evaluate_ec2(
                session,
                client_id,
                aws_account.id
            )
            total += RightsizingEngine.evaluate_rds(
                session,
                client_id,
                aws_account.id
            )

        return total

    # =====================================================
    # EC2 RIGHTSIZING
    # =====================================================
    @staticmethod
    def evaluate_ec2(session, client_id, aws_account_id):

        count = 0

        instances = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            aws_account_id=aws_account_id,
            service_name="EC2",
            resource_type="Instance",
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

            try:
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
            except Exception as e:
                print(f"[EC2 RIGHTSIZING ERROR]: {str(e)}")
                continue

            datapoints = metrics.get("Datapoints", [])

            if not datapoints:
                continue

            avg_cpu = sum(d["Average"] for d in datapoints) / len(datapoints)

            print(f"EC2: {instance_id} | Avg CPU: {avg_cpu}")

            if avg_cpu < 10:

                AWSFinding.upsert_finding(
                    client_id=client_id,
                    aws_account_id=instance.aws_account_id,
                    resource_id=instance_id,
                    resource_type="EC2",
                    aws_service="EC2",
                    finding_type="EC2_UNDERUTILIZED",
                    severity="MEDIUM",
                    message=f"Average CPU last 7 days: {round(avg_cpu,2)}%",
                    estimated_monthly_savings=100.0
                )

                count += 1

        return count

    # =====================================================
    # RDS RIGHTSIZING
    # =====================================================
    @staticmethod
    def evaluate_rds(session, client_id, aws_account_id):

        count = 0

        rds_instances = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            aws_account_id=aws_account_id,
            service_name="RDS",
            resource_type="DBInstance",
            is_active=True
        ).all()

        for db_instance in rds_instances:

            if db_instance.state != "available":
                continue

            region = db_instance.region
            db_identifier = db_instance.resource_id

            cloudwatch = session.client(
                "cloudwatch",
                region_name=region
            )

            end = datetime.utcnow()
            start = end - timedelta(days=7)

            try:
                metrics = cloudwatch.get_metric_statistics(
                    Namespace="AWS/RDS",
                    MetricName="CPUUtilization",
                    Dimensions=[
                        {"Name": "DBInstanceIdentifier", "Value": db_identifier}
                    ],
                    StartTime=start,
                    EndTime=end,
                    Period=86400,
                    Statistics=["Average"]
                )
            except Exception as e:
                print(f"[RDS RIGHTSIZING ERROR]: {str(e)}")
                continue

            datapoints = metrics.get("Datapoints", [])

            if not datapoints:
                continue

            avg_cpu = sum(d["Average"] for d in datapoints) / len(datapoints)

            print(f"RDS: {db_identifier} | Avg CPU: {avg_cpu}")

            if avg_cpu < 10:

                AWSFinding.upsert_finding(
                    client_id=client_id,
                    aws_account_id=db_instance.aws_account_id,
                    resource_id=db_identifier,
                    resource_type="RDS",
                    aws_service="RDS",
                    finding_type="RDS_UNDERUTILIZED",
                    severity="MEDIUM",
                    message=f"RDS average CPU last 7 days: {round(avg_cpu,2)}%",
                    estimated_monthly_savings=50.0
                )

                count += 1

        return count
