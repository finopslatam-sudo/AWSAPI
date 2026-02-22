from src.aws.finding_engine.ec2_rules import EC2Rules
from src.aws.finding_engine.ebs_rules import EBSRules


class FindingEngine:

    @staticmethod
    def run(client_id: int):

        total_findings = 0

        total_findings += EC2Rules.stopped_instances_rule(client_id)
        total_findings += EBSRules.unattached_volumes_rule(client_id)

        return total_findings