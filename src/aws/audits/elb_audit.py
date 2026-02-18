from .base_audit import BaseAudit
from src.models.database import db


class ELBAudit(BaseAudit):

    def run(self):
        elbv2 = self.session.client("elbv2")
        findings_created = 0
        active_lbs = []

        load_balancers = elbv2.describe_load_balancers()

        for lb in load_balancers["LoadBalancers"]:

            lb_arn = lb["LoadBalancerArn"]

            target_groups = elbv2.describe_target_groups(
                LoadBalancerArn=lb_arn
            )

            if not target_groups["TargetGroups"]:

                active_lbs.append(lb_arn)

                created = self.create_or_reopen_finding(
                    resource_id=lb_arn,
                    resource_type="ELB",
                    finding_type="IDLE_LOAD_BALANCER",
                    severity="MEDIUM",
                    message="Load balancer has no target groups attached",
                    estimated_monthly_savings=18
                )

                if created:
                    findings_created += 1

        self.resolve_missing_findings(
            active_resource_ids=active_lbs,
            finding_type="IDLE_LOAD_BALANCER"
        )

        db.session.commit()
        return findings_created
