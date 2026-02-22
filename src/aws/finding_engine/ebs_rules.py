from datetime import datetime
from sqlalchemy import and_
from src.models.database import db
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class EBSRules:

    @staticmethod
    def unattached_volumes_rule(client_id: int):

        # ================================
        # 1️⃣ Buscar EBS available en inventory
        # ================================
        unattached_volumes = AWSResourceInventory.query.filter(
            and_(
                AWSResourceInventory.client_id == client_id,
                AWSResourceInventory.resource_type == "EBS",
                AWSResourceInventory.state == "available",
                AWSResourceInventory.is_active == True
            )
        ).all()

        findings_created = 0

        for volume in unattached_volumes:

            # ================================
            # 2️⃣ Verificar si ya existe finding activo
            # ================================
            existing = AWSFinding.query.filter_by(
                client_id=client_id,
                resource_id=volume.resource_id,
                finding_type="UNATTACHED_VOLUME",
                resolved=False
            ).first()

            if existing:
                continue

            # ================================
            # 3️⃣ Crear finding
            # ================================
            finding = AWSFinding(
                client_id=client_id,
                aws_account_id=volume.aws_account_id,
                resource_id=volume.resource_id,
                resource_type="EBS",
                finding_type="UNATTACHED_VOLUME",
                severity="HIGH",
                message="EBS volume not attached to any instance",
                estimated_monthly_savings=5.0,
                detected_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
                resolved=False
            )

            db.session.add(finding)
            findings_created += 1

        db.session.commit()

        return findings_created