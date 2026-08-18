from src.models.database import db
from src.models.encrypted_types import EncryptedString
from datetime import datetime


class GCPAccount(db.Model):
    """
    Cuenta GCP conectada por un cliente (equivalente a AWSAccount/AzureAccount).

    Auth GCP vs AWS/Azure: GCP usa una Service Account con su JSON key
    completo (no un solo secreto simple como client_secret de Azure ni
    un role_arn como AWS). Por eso se cifra el JSON completo como texto.
    """

    __tablename__ = 'gcp_accounts'

    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey('clients.id'),
        nullable=False
    )

    project_id = db.Column(db.String(100), nullable=False)
    project_name = db.Column(db.String(150), nullable=False)

    service_account_email = db.Column(db.String(255), nullable=False)

    # Cifrado en reposo (Fernet, ver encrypted_types.EncryptedString) —
    # misma clave/infra que AWSAccount/AzureAccount, sin duplicar el mecanismo.
    # Guarda el JSON completo de la Service Account key.
    service_account_key = db.Column(
        EncryptedString(4096, env_var="AWS_SECRET_ENCRYPTION_KEY"),
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
            "project_id": self.project_id,
            "project_name": self.project_name,
            "service_account_email": self.service_account_email,
            "is_active": self.is_active,

            "last_sync": self.last_sync.isoformat() if self.last_sync else None,

            "audit_status": self.audit_status,
            "audit_started_at": self.audit_started_at.isoformat() if self.audit_started_at else None,
            "audit_finished_at": self.audit_finished_at.isoformat() if self.audit_finished_at else None,

            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
