from datetime import datetime
from sqlalchemy import and_
from src.models.database import db
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class EC2Rules:

    @staticmethod
    def stopped_instances_rule(client_id: int):

        # ================================
        # 1️⃣ Buscar EC2 stopped en inventory
        # ================================
        stopped_instances = AWSResourceInventory.query.filter(
            and_(
                AWSResourceInventory.client_id == client_id,
                AWSResourceInventory.resource_type == "EC2",
                AWSResourceInventory.state == "stopped",
                AWSResourceInventory.is_active == True
            )
        ).all()

        findings_created = 0

        for instance in stopped_instances:

            # ================================
            # 2️⃣ Verificar si ya existe finding activo
            # ================================
            existing = AWSFinding.query.filter_by(
                client_id=client_id,
                resource_id=instance.resource_id,
                finding_type="STOPPED_INSTANCE",
                resolved=False
            ).first()

            if existing:
                continue

            # ================================
            # 3️⃣ Crear nuevo finding
            # ================================
            finding = AWSFinding(
                client_id=client_id,
                aws_account_id=instance.aws_account_id,
                resource_id=instance.resource_id,
                resource_type="EC2",
                finding_type="STOPPED_INSTANCE",
                severity="MEDIUM",
                message="EC2 instance is stopped",
                estimated_monthly_savings=10.0,  # puedes mejorar lógica luego
                detected_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
                resolved=False
            )

            db.session.add(finding)
            findings_created += 1

        db.session.commit()

        return findings_created