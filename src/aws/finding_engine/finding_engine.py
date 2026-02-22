from src.aws.finding_engine.ec2_rules import EC2Rules


class FindingEngine:

    @staticmethod
    def run(client_id: int):

        total_findings = 0

        # Ejecutar reglas
        total_findings += EC2Rules.stopped_instances_rule(client_id)

        return total_findings