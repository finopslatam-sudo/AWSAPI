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
    # ROLE HELPERS (CLARITY)
    # ==========================
    def is_root_user(self) -> bool:
        return self.is_root is True

    def is_admin_user(self) -> bool:
        return self.role == "admin"

    def is_client_user(self) -> bool:
        return self.role == "client"

    # ==========================
    # DOMAIN PERMISSIONS (CRITICAL)
    # ==========================
    def can_be_modified_by(self, actor: "Client") -> bool:
        """
        Enterprise-grade domain permission rules.

        Rules:
        - ROOT can modify anyone (including itself)
        - ADMIN can modify CLIENT only
        - ADMIN cannot modify ADMIN or ROOT
        - CLIENT cannot modify anyone
        """

        # Sanity check
        if not actor:
            return False

        # ROOT can do everything
        if actor.is_root_user():
            return True

        # Target is ROOT → nobody except ROOT
        if self.is_root_user():
            return False

        # ADMIN rules
        if actor.is_admin_user():
            # Admin can modify clients only
            return self.is_client_user()

        # CLIENT can modify nobody
        return False

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
        NEVER expose is_root or password hash.
        """
        return {
            "id": self.id,
            "company_name": self.company_name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }
