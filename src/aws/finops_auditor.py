import boto3
from botocore.exceptions import ClientError
from src.aws.sts_service import STSService

from src.aws.audits.ec2_audit import EC2Audit
from src.aws.audits.ebs_audit import EBSAudit
from src.aws.audits.tag_audit import TagAudit
from src.aws.audits.s3_audit import S3Audit
from src.aws.audits.snapshot_audit import SnapshotAudit
from src.aws.audits.eip_audit import EIPAudit
from src.aws.audits.elb_audit import ELBAudit

from src.aws.inventory_scanner import InventoryScanner


class FinOpsAuditor:

    def run_comprehensive_audit(self, client_id, aws_account):

        sts_service = STSService()

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

        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name="us-east-1"
        )

        # ================================
        # 1️⃣ INVENTORY SCAN (PRIMERO)
        # ================================
        try:
            scanner = InventoryScanner(session, client_id, aws_account)
            scanner.run()
        except Exception as e:
            print(f"[INVENTORY ERROR]: {str(e)}")

        # ================================
        # 2️⃣ AUDITS
        # ================================
        audits = [
            EC2Audit(session, client_id, aws_account),
            EBSAudit(session, client_id, aws_account),
            TagAudit(session, client_id, aws_account),
            S3Audit(session, client_id, aws_account),
            SnapshotAudit(session, client_id, aws_account),
            EIPAudit(session, client_id, aws_account),
            ELBAudit(session, client_id, aws_account),
        ]

        total_findings = 0

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