from src.models.database import db
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime


class AWSFinding(db.Model):
    __tablename__ = "aws_findings"

    id = db.Column(db.Integer, primary_key=True)

    # ---------------- TENANT RELATION ----------------
    client_id = db.Column(
        db.Integer,
        db.ForeignKey("clients.id"),
        nullable=False
    )

    aws_account_id = db.Column(
        db.Integer,
        db.ForeignKey("aws_accounts.id"),
        nullable=False
    )

    # ---------------- RESOURCE INFO ----------------
    resource_id = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)

    # ✅ NUEVO CAMPO ENTERPRISE
    aws_service = db.Column(
        db.String(50),
        nullable=False
    )

    # ---------------- FINDING METADATA ----------------
    finding_type = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False)

    message = db.Column(db.Text, nullable=False)

    estimated_monthly_savings = db.Column(
        db.Numeric(10, 2),
        default=0
    )

    # ---------------- LIFECYCLE MANAGEMENT ----------------
    resolved = db.Column(
        db.Boolean,
        default=False
    )

    resolved_at = db.Column(
        db.DateTime,
        nullable=True
    )

    resolved_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    # ---------------- TIMESTAMPS ----------------
    detected_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    resolver = db.relationship(
        "User",
        foreign_keys=[resolved_by],
        lazy="joined"
    )

    # =====================================================
    # ENTERPRISE UPSERT (ACTUALIZADO)
    # =====================================================
    @staticmethod
    def upsert_finding(
        client_id,
        aws_account_id,
        resource_id,
        resource_type,
        aws_service,
        finding_type,
        severity,
        message,
        estimated_monthly_savings=None
    ):

        now = datetime.utcnow()

        stmt = insert(AWSFinding).values(
            client_id=client_id,
            aws_account_id=aws_account_id,
            resource_id=resource_id,
            resource_type=resource_type,
            aws_service=aws_service,
            finding_type=finding_type,
            severity=severity,
            message=message,
            estimated_monthly_savings=estimated_monthly_savings,
            resolved=False,
            detected_at=now,
            created_at=now
        )

        stmt = stmt.on_conflict_do_update(
            constraint="uq_client_resource_type",
            set_={
                "severity": severity,
                "message": message,
                "estimated_monthly_savings": estimated_monthly_savings,
                "resolved": False,
                "detected_at": now,
                "resource_type": resource_type,
                "aws_service": aws_service,
            }
        )

        result = db.session.execute(stmt)

        db.session.flush()

        return True