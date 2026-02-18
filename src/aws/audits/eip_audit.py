from .base_audit import BaseAudit
from src.models.database import db


class EIPAudit(BaseAudit):

    def run(self):
        ec2 = self.session.client("ec2")
        findings_created = 0
        active_eips = []

        addresses = ec2.describe_addresses()

        for address in addresses["Addresses"]:

            # Si no está asociado a ninguna instancia
            if "AssociationId" not in address:

                eip_id = address.get("AllocationId", address.get("PublicIp"))
                active_eips.append(eip_id)

                created = self.create_or_reopen_finding(
                    resource_id=eip_id,
                    resource_type="ElasticIP",
                    finding_type="UNUSED_ELASTIC_IP",
                    severity="HIGH",
                    message="Elastic IP is not associated with any resource",
                    estimated_monthly_savings=3
                )

                if created:
                    findings_created += 1

        self.resolve_missing_findings(
            active_resource_ids=active_eips,
            finding_type="UNUSED_ELASTIC_IP"
        )

        db.session.commit()
        return findings_created
