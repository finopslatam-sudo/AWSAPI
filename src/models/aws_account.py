from src.models.database import db
from datetime import datetime


class AWSAccount(db.Model):
    __tablename__ = 'aws_accounts'

    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey('clients.id'),
        nullable=False
    )

    account_id = db.Column(db.String(12), nullable=False)
    account_name = db.Column(db.String(100), nullable=False)

    role_arn = db.Column(db.String(255), nullable=False)
    external_id = db.Column(
    db.String(64),
    nullable=False,
    index=True
    )

    is_active = db.Column(db.Boolean, default=True)

    # ==========================================
    # SINCRONIZACIÓN INVENTORY
    # ==========================================
    last_sync = db.Column(db.DateTime)

    # ==========================================
    # NUEVO — ESTADO AUDIT ASYNC
    # ==========================================
    audit_status = db.Column(
        db.String(20),
        default="idle"  # idle | running | completed | failed
    )

    audit_started_at = db.Column(db.DateTime)
    audit_finished_at = db.Column(db.DateTime)

    # ==========================================
    # METADATA
    # ==========================================
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # ==========================================
    # SERIALIZER
    # ==========================================
    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "account_name": self.account_name,
            "is_active": self.is_active,

            "last_sync": self.last_sync.isoformat() if self.last_sync else None,

            # 🔥 NUEVO
            "audit_status": self.audit_status,
            "audit_started_at": self.audit_started_at.isoformat() if self.audit_started_at else None,
            "audit_finished_at": self.audit_finished_at.isoformat() if self.audit_finished_at else None,

            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }