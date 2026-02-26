from src.aws.finding_engine.ec2_rules import EC2Rules
from src.aws.finding_engine.ebs_rules import EBSRules
from src.aws.finding_engine.tag_rules import TagRules
from src.aws.finding_engine.rds_rules import RDSRules
from src.aws.finding_engine.lambda_rules import LambdaRules
from src.aws.finding_engine.dynamodb_rules import DynamoDBRules
from src.aws.finding_engine.cloudwatch_rules import CloudWatchRules
from src.aws.finding_engine.rightsizing_rules import RightsizingRules
from src.aws.finding_engine.ri_rules import ReservedInstanceRules
from src.aws.finding_engine.savings_plan_rules import SavingsPlanRules
from src.aws.finops.rightsizing_engine import RightsizingEngine
from src.aws.finops.coverage_engine import CoverageEngine
from src.aws.finops.sp_coverage_engine import SavingsPlanCoverageEngine

from src.models.aws_finding import AWSFinding
from src.models.database import db


class FindingEngine:

    # =====================================================
    # MAIN ENTRYPOINT (ENTERPRISE TRANSACTION SAFE)
    # =====================================================
    @staticmethod
    def run(client_id: int):

        total_findings = 0

        try:

            # =====================================================
            # 🔒 TRANSACCION CONTROLADA SIN AUTOFLUSH
            # =====================================================
            with db.session.no_autoflush:

                # =====================================================
                # 1️⃣ MARCAR TODOS LOS FINDINGS COMO POTENCIALMENTE RESUELTOS
                # =====================================================
                AWSFinding.query.filter_by(
                    client_id=client_id
                ).update({
                    "resolved": True
                })

                # =====================================================
                # 2️⃣ EJECUTAR REGLAS BASE
                # =====================================================

                total_findings += EC2Rules.stopped_instances_rule(client_id)
                total_findings += EBSRules.unattached_volumes_rule(client_id)
                total_findings += TagRules.missing_required_tags_rule(client_id)
                total_findings += RDSRules.run_all(client_id)
                total_findings += LambdaRules.run_all(client_id)
                total_findings += DynamoDBRules.run_all(client_id)
                total_findings += CloudWatchRules.run_all(client_id)

                # =====================================================
                # 3️⃣ FINOPS CLASSIC RULES
                # =====================================================

                total_findings += ReservedInstanceRules.unused_ri_rule(client_id)
                total_findings += SavingsPlanRules.review_active_plans_rule(client_id)
                total_findings += RightsizingRules.ec2_oversized_rule(client_id)

                # =====================================================
                # 4️⃣ FINOPS ENGINES AVANZADOS
                # =====================================================

                total_findings += RightsizingEngine.run(client_id)
                total_findings += CoverageEngine.run(client_id)
                total_findings += SavingsPlanCoverageEngine.run(client_id)

            # =====================================================
            # 5️⃣ SINGLE ENTERPRISE COMMIT
            # =====================================================
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(f"[FINDING ENGINE TRANSACTION ERROR]: {str(e)}")
            return 0

        return total_findings