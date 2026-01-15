from src.models.database import db
from datetime import datetime
import bcrypt

from datetime import datetime
from src.models.database import db


class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    contact_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))

    is_active = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(20), default="client", nullable=False)

    force_password_change = db.Column(db.Boolean, default=False)
    password_expires_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ==========================
    # PASSWORD HELPERS
    # ==========================
    def set_password(self, password: str):
        import bcrypt
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, password: str) -> bool:
        if not password or not self.password_hash:
            return False
        try:
            import bcrypt
            return bcrypt.checkpw(
                password.encode("utf-8"),
                self.password_hash.encode("utf-8")
            )
        except Exception:
            return False

    def to_dict(self):
        return {
            "id": self.id,
            "company_name": self.company_name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
        }

