from decimal import Decimal
from datetime import datetime
from src.models.aws_finding import AWSFinding
from src.models.database import db
from src.aws.sts_service import STSService
import boto3


class FinOpsAuditor:

    def run_comprehensive_audit(self, client_id, aws_account):
        """
        Ejecuta auditoría completa y guarda findings en DB
        """

        # 1️⃣ Assume Role
        sts_service = STSService()
        creds = sts_service.assume_role(
            role_arn=aws_account.role_arn,
            external_id=aws_account.external_id
        )

        # 2️⃣ Crear cliente EC2 con credenciales temporales
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name="us-east-1"
        )

        findings_created = 0

        # =====================================================
        # REGLA 1 — EBS HUÉRFANOS
        # =====================================================

        volumes = ec2.describe_volumes()

        for v in volumes["Volumes"]:
            if v["State"] == "available":

                finding = AWSFinding(
                    client_id=client_id,
                    aws_account_id=aws_account.id,
                    resource_id=v["VolumeId"],
                    resource_type="EBS",
                    finding_type="UNATTACHED_VOLUME",
                    severity="HIGH",
                    message=f"Volumen {v['VolumeId']} no está adjunto y genera costo innecesario",
                    estimated_monthly_savings=Decimal("5.00"),  # estimado simple
                    detected_at=datetime.utcnow()
                )

                db.session.add(finding)
                findings_created += 1

        # =====================================================
        # REGLA 2 — EC2 STOPPED
        # =====================================================

        instances = ec2.describe_instances()

        for reservation in instances["Reservations"]:
            for instance in reservation["Instances"]:

                if instance["State"]["Name"] == "stopped":

                    finding = AWSFinding(
                        client_id=client_id,
                        aws_account_id=aws_account.id,
                        resource_id=instance["InstanceId"],
                        resource_type="EC2",
                        finding_type="STOPPED_INSTANCE",
                        severity="MEDIUM",
                        message=f"Instancia {instance['InstanceId']} detenida",
                        estimated_monthly_savings=Decimal("10.00"),
                        detected_at=datetime.utcnow()
                    )

                    db.session.add(finding)
                    findings_created += 1

        db.session.commit()

        return {
            "status": "ok",
            "findings_created": findings_created
        }
