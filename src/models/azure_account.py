from src.models.database import db
from src.models.encrypted_types import EncryptedString
from datetime import datetime


class AzureAccount(db.Model):
    """
    Cuenta Azure conectada por un cliente (equivalente a AWSAccount).

    Auth Azure vs AWS: Azure usa Service Principal (Tenant ID + App
    Client ID + Client Secret) contra una Subscription, no AssumeRole
    con ExternalId. Por eso los nombres de columna son distintos a
    AWSAccount — no es un simple rename, es un modelo de credenciales
    diferente.
    """

    __tablename__ = 'azure_accounts'

    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey('clients.id'),
        nullable=False
    )

    subscription_id = db.Column(db.String(36), nullable=False)
    subscription_name = db.Column(db.String(100), nullable=False)

    tenant_id = db.Column(db.String(36), nullable=False)
    app_client_id = db.Column(db.String(36), nullable=False)

    # Cifrado en reposo (Fernet, ver encrypted_types.EncryptedString) —
    # misma clave/infra que AWSAccount.role_arn, sin duplicar el mecanismo.
    client_secret = db.Column(
        EncryptedString(512, env_var="AWS_SECRET_ENCRYPTION_KEY"),
        nullable=False
    )

    is_active = db.Column(db.Boolean, default=True)

    # ==========================================
    # SINCRONIZACIÓN INVENTORY
    # ==========================================
    last_sync = db.Column(db.DateTime)

    # ==========================================
    # ESTADO AUDIT ASYNC
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
            "subscription_id": self.subscription_id,
            "subscription_name": self.subscription_name,
            "is_active": self.is_active,

            "last_sync": self.last_sync.isoformat() if self.last_sync else None,

            "audit_status": self.audit_status,
            "audit_started_at": self.audit_started_at.isoformat() if self.audit_started_at else None,
            "audit_finished_at": self.audit_finished_at.isoformat() if self.audit_finished_at else None,

            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
