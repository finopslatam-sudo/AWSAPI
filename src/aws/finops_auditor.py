import boto3
from botocore.exceptions import ClientError
from src.aws.sts_service import STSService
from src.aws.audits.ec2_audit import EC2Audit
from src.aws.audits.ebs_audit import EBSAudit


class FinOpsAuditor:

    def run_comprehensive_audit(self, client_id, aws_account):

        sts_service = STSService()

        # 1️⃣ Asumir role en cuenta cliente
        creds = sts_service.assume_role(
            role_arn=aws_account.role_arn,
            external_id=aws_account.external_id,
            session_name="finops-audit"
        )

        if not creds:
            return {
                "status": "error",
                "message": "Unable to assume role",
                "findings_created": 0
            }

        # 2️⃣ Crear sesión temporal
        session = boto3.Session(
            aws_access_key_id=creds["access_key"],
            aws_secret_access_key=creds["secret_key"],
            aws_session_token=creds["session_token"],
            region_name="us-east-1"
        )

        # 3️⃣ Registrar auditorías activas
        audits = [
            EC2Audit(session, client_id, aws_account),
            EBSAudit(session, client_id, aws_account)
        ]

        total_findings = 0

        # 4️⃣ Ejecutar auditorías con protección de errores
        for audit in audits:
            try:
                created = audit.run()
                total_findings += created
            except ClientError as e:
                print(f"[AWS ERROR] {audit.__class__.__name__}: {str(e)}")
            except Exception as e:
                print(f"[INTERNAL ERROR] {audit.__class__.__name__}: {str(e)}")

        return {
            "status": "ok",
            "findings_created": total_findings
        }
