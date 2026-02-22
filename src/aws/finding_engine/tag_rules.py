from datetime import datetime
from sqlalchemy import and_
from src.models.database import db
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class TagRules:

    REQUIRED_TAGS = ["Owner", "Environment"]

    @staticmethod
    def missing_required_tags_rule(client_id: int):

        resources = AWSResourceInventory.query.filter(
            and_(
                AWSResourceInventory.client_id == client_id,
                AWSResourceInventory.is_active == True
            )
        ).all()

        findings_created = 0

        for resource in resources:

            tags = resource.tags or {}

            for required_tag in TagRules.REQUIRED_TAGS:

                if required_tag not in tags:

                    finding_type = f"MISSING_TAG_{required_tag.upper()}"

                    existing = AWSFinding.query.filter_by(
                        client_id=client_id,
                        resource_id=resource.resource_id,
                        finding_type=finding_type,
                        resolved=False
                    ).first()

                    if existing:
                        continue

                    finding = AWSFinding(
                        client_id=client_id,
                        aws_account_id=resource.aws_account_id,
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        finding_type=finding_type,
                        severity="LOW",
                        message=f"Missing required tag: {required_tag}",
                        estimated_monthly_savings=0.0,
                        detected_at=datetime.utcnow(),
                        created_at=datetime.utcnow(),
                        resolved=False
                    )

                    db.session.add(finding)
                    findings_created += 1

        db.session.commit()

        return findings_created