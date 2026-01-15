from datetime import datetime
from src.models.database import db
import bcrypt


class Client(db.Model):
    __tablename__ = "clients"

    # ==========================
    # CORE FIELDS
    # ==========================
    id = db.Column(db.Integer, primary_key=True)

    company_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    password_hash = db.Column(db.String(255), nullable=False)

    contact_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))

    # ==========================
    # SECURITY & ACCESS CONTROL
    # ==========================
    role = db.Column(db.String(20), default="client", nullable=False)
    is_root = db.Column(db.Boolean, default=False, nullable=False)

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    force_password_change = db.Column(db.Boolean, default=False)
    password_expires_at = db.Column(db.DateTime, nullable=True)

    # ==========================
    # AUDIT
    # ==========================
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # ==========================
    # DOMAIN HELPERS (IMPORTANT)
    # ==========================
    def is_protected(self) -> bool:
        """
        ROOT users are immutable from administrative actions
        """
        return self.is_root is True

    def can_be_modified_by(self, actor: "Client") -> bool:
        """
        Domain-level permission check.
        This MUST be respected by use cases.
        """

        # ROOT cannot be modified by anyone
        if self.is_root:
            return False

        # Admin cannot modify another admin
        if self.role == "admin" and actor.role != "root":
            return False

        # Regular users cannot modify anyone
        if actor.role == "client":
            return False

        return True

    # ==========================
    # PASSWORD HELPERS
    # ==========================
    def set_password(self, password: str):
        if not password:
            raise ValueError("Password cannot be empty")

        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, password: str) -> bool:
        if not password or not self.password_hash:
            return False

        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                self.password_hash.encode("utf-8")
            )
        except Exception:
            return False

    # ==========================
    # SERIALIZATION
    # ==========================
    def to_dict(self):
        """
        Public-safe representation.
        NEVER expose is_root.
        """
        return {
            "id": self.id,
            "company_name": self.company_name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }
