from src.aws.finding_engine.ec2_rules import EC2Rules
from src.aws.finding_engine.ebs_rules import EBSRules
from src.aws.finding_engine.tag_rules import TagRules
from src.aws.finding_engine.rds_rules import RDSRules
from src.aws.finding_engine.lambda_rules import LambdaRules
from src.aws.finding_engine.dynamodb_rules import DynamoDBRules
from src.aws.finding_engine.cloudwatch_rules import CloudWatchRules

from src.models.database import db


class FindingEngine:

    # =====================================================
    # MAIN ENTRYPOINT (ENTERPRISE TRANSACTION SAFE)
    # =====================================================
    @staticmethod
    def run(client_id: int):

        total_findings = 0

        try:

            # ===============================
            # EC2
            # ===============================
            total_findings += EC2Rules.stopped_instances_rule(client_id)

            # ===============================
            # EBS
            # ===============================
            total_findings += EBSRules.unattached_volumes_rule(client_id)

            # ===============================
            # TAG GOVERNANCE
            # ===============================
            total_findings += TagRules.missing_required_tags_rule(client_id)

            # ===============================
            # RDS
            # ===============================
            total_findings += RDSRules.run_all(client_id)

            # ===============================
            # LAMBDA
            # ===============================
            total_findings += LambdaRules.run_all(client_id)

            # ===============================
            # DYNAMODB
            # ===============================
            total_findings += DynamoDBRules.run_all(client_id)

            # ===============================
            # CLOUDWATCH
            # ===============================
            total_findings += CloudWatchRules.run_all(client_id)

            # =====================================================
            # 🔥 SINGLE ENTERPRISE COMMIT
            # =====================================================
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(f"[FINDING ENGINE TRANSACTION ERROR]: {str(e)}")
            return 0

        return total_findings