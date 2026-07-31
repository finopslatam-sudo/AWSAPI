import logging

from src.aws.scanners.shared import BaseScanner


logger = logging.getLogger(__name__)


class ELBScanner(BaseScanner):
    """Handles Load Balancers: ALB/NLB (elbv2) and Classic ELB."""

    # ------------------------------------------------------------------
    # ALB / NLB
    # ------------------------------------------------------------------
    def scan_load_balancers(self, region):
        try:
            elbv2 = self.aws_session.client("elbv2", region_name=region)
            paginator = elbv2.get_paginator("describe_load_balancers")

            for page in paginator.paginate():
                for lb in page.get("LoadBalancers", []):
                    lb_arn = lb["LoadBalancerArn"]

                    target_groups = elbv2.describe_target_groups(
                        LoadBalancerArn=lb_arn
                    ).get("TargetGroups", [])

                    self.upsert_resource(
                        service_name="ELB",
                        resource_type=lb.get("Type", "application"),
                        resource_id=lb_arn,
                        region=region,
                        state=lb.get("State", {}).get("Code"),
                        tags={},
                        resource_metadata={
                            "name": lb.get("LoadBalancerName"),
                            "scheme": lb.get("Scheme"),
                            "dns_name": lb.get("DNSName"),
                            "target_group_count": len(target_groups),
                        }
                    )

        except Exception:
            logger.exception(f"ALB/NLB scan failed | region={region}")
            raise

    # ------------------------------------------------------------------
    # CLASSIC ELB
    # ------------------------------------------------------------------
    def scan_classic_load_balancers(self, region):
        try:
            elb = self.aws_session.client("elb", region_name=region)
            paginator = elb.get_paginator("describe_load_balancers")

            for page in paginator.paginate():
                for lb in page.get("LoadBalancerDescriptions", []):
                    name = lb["LoadBalancerName"]
                    instances = lb.get("Instances", [])

                    self.upsert_resource(
                        service_name="ELB",
                        resource_type="classic",
                        resource_id=f"classic-{region}-{name}",
                        region=region,
                        state="active",
                        tags={},
                        resource_metadata={
                            "name": name,
                            "dns_name": lb.get("DNSName"),
                            "instance_count": len(instances),
                        }
                    )

        except Exception:
            logger.exception(f"Classic ELB scan failed | region={region}")
            raise
