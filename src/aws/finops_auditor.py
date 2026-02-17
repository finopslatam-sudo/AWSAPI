from src.aws.sts_service import STSService


class FinOpsAuditor:

    def run_comprehensive_audit(self, role_arn, external_id):
        creds = STSService.assume_role(role_arn, external_id)

        return {
            "status": "ok",
            "assumed": True,
            "access_key_prefix": creds["access_key"][:4]
        }
