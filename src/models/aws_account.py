from src.models.database import db
from src.models.encrypted_types import EncryptedString
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

    # Cifrados en reposo (Fernet, ver encrypted_types.EncryptedString).
    # NOTA: el índice ya no acelera lookups por valor exacto (el
    # ciphertext de Fernet es no-determinístico) — se mantiene solo
    # porque nada hoy hace filter_by(external_id=...) de todas formas.
    role_arn = db.Column(EncryptedString(512, env_var="AWS_SECRET_ENCRYPTION_KEY"), nullable=False)
    external_id = db.Column(
        EncryptedString(255, env_var="AWS_SECRET_ENCRYPTION_KEY"),
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
    # ANOMALY DETECTION
    # ==========================================
    anomaly_monitor_arn = db.Column(db.String(255), nullable=True)

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