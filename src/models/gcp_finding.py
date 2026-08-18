from src.models.database import db
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime


class GCPFinding(db.Model):
    """Equivalente a AWSFinding/AzureFinding, tabla propia. Mismo patrón
    de upsert idempotente con auto-resolución usado por el finding
    engine de AWS y Azure."""

    __tablename__ = "gcp_findings"

    __table_args__ = (
        db.UniqueConstraint(
            "client_id", "resource_id", "finding_type",
            name="uq_gcp_client_resource_type"
        ),
        db.Index("idx_gcp_findings_client_resolved", "client_id", "resolved"),
        db.Index("idx_gcp_findings_resource_client", "resource_id", "client_id"),
        db.Index(
            "idx_gcp_findings_resource_client_resolved",
            "resource_id", "client_id", "resolved"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey("clients.id"),
        nullable=False
    )

    gcp_account_id = db.Column(
        db.Integer,
        db.ForeignKey("gcp_accounts.id"),
        nullable=False
    )

    resource_id = db.Column(db.String(300), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)
    region = db.Column(db.String(50), nullable=True)

    gcp_service = db.Column(
        db.String(50),
        nullable=False
    )

    finding_type = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False)

    message = db.Column(db.Text, nullable=False)

    estimated_monthly_savings = db.Column(
        db.Numeric(10, 2),
        default=0
    )

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

    @staticmethod
    def upsert_finding(
        client_id,
        gcp_account_id,
        resource_id,
        resource_type,
        gcp_service,
        finding_type,
        severity,
        message,
        estimated_monthly_savings=None,
        region=None
    ):

        now = datetime.utcnow()

        stmt = insert(GCPFinding).values(
            client_id=client_id,
            gcp_account_id=gcp_account_id,
            resource_id=resource_id,
            resource_type=resource_type,
            region=region,
            gcp_service=gcp_service,
            finding_type=finding_type,
            severity=severity,
            message=message,
            estimated_monthly_savings=estimated_monthly_savings,
            resolved=False,
            detected_at=now,
            created_at=now
        )

        stmt = stmt.on_conflict_do_update(
            constraint="uq_gcp_client_resource_type",
            set_={
                "severity": severity,
                "message": message,
                "estimated_monthly_savings": estimated_monthly_savings,
                "resolved": False,
                "detected_at": now,
                "resource_type": resource_type,
                "gcp_service": gcp_service,
                "region": region,
            }
        )

        db.session.execute(stmt)
        db.session.flush()

        return True
