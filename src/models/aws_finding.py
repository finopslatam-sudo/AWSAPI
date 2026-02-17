from src.models.database import db
from datetime import datetime

class AWSFinding(db.Model):
    __tablename__ = "aws_findings"

    id = db.Column(db.Integer, primary_key=True)

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

    resource_id = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)

    finding_type = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False)

    message = db.Column(db.Text, nullable=False)

    estimated_monthly_savings = db.Column(
        db.Numeric(10, 2),
        default=0
    )

    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime)

    detected_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
