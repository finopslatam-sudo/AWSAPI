from datetime import datetime

from src.models.database import db
from src.models.aws_account import AWSAccount


class AlertPolicy(db.Model):
    __tablename__ = 'alert_policies'

    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey('clients.id'),
        nullable=False,
        index=True
    )

    aws_account_id = db.Column(
        db.Integer,
        db.ForeignKey('aws_accounts.id'),
        nullable=True,
        index=True
    )

    policy_id = db.Column(db.String(64), nullable=False)  # ej: budget-monthly, anomaly-spike
    title = db.Column(db.String(255), nullable=False)

    channel = db.Column(db.String(20), nullable=False)  # email | slack | teams (future)
    email = db.Column(db.String(255), nullable=True)

    threshold = db.Column(db.Float, nullable=True)
    threshold_type = db.Column(db.String(10), nullable=True)  # USD | %
    period = db.Column(db.String(20), nullable=True)  # monthly | annual | daily | weekly

    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_fired_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self, include_account: bool = True):
        account = None

        if include_account and self.aws_account_id:
            account = AWSAccount.query.get(self.aws_account_id)

        data = {
            "id": self.id,
            "client_id": self.client_id,
            "aws_account_id": self.aws_account_id,
            "policy_id": self.policy_id,
            "title": self.title,
            "channel": self.channel,
            "email": self.email,
            "threshold": self.threshold,
            "threshold_type": self.threshold_type,
            "period": self.period,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            # Compatibilidad con frontend que consume campos planos.
            "account_name": account.account_name if account else None,
            "aws_account_name": account.account_name if account else None,
            "account_id": account.account_id if account else None,
            "aws_account_number": account.account_id if account else None,
        }

        if account:
            data["account"] = account.to_dict() if account else None

        return data
