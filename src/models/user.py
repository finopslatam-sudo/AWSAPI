"""
USER MODEL
==========

Modelo de usuario FinOpsLatam.
Soporta hashes legacy (PBKDF2) y modernos (bcrypt).
Migra automáticamente a bcrypt en login exitoso.
"""

from datetime import datetime
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from werkzeug.security import check_password_hash
from .database import db

# ==========================
# PASSWORD CONTEXT
# ==========================
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(120), unique=True, nullable=False, index=True)

    password_hash = db.Column(db.String(255), nullable=False)

    # ==========================
    # ROLES
    # ==========================
    global_role = db.Column(db.String(50), nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=True)
    client_role = db.Column(db.String(50), nullable=True)

    # ==========================
    # SECURITY FLAGS
    # ==========================
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    force_password_change = db.Column(db.Boolean, default=False, nullable=False)
    password_expires_at = db.Column(db.DateTime, nullable=True)

    # ==========================
    # AUDIT
    # ==========================
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # ==========================
    # PASSWORD METHODS
    # ==========================
    def set_password(self, password: str) -> None:
        """
        Guarda la contraseña usando bcrypt (estándar actual).
        """
        self.password_hash = pwd_context.hash(password)

    def check_password(self, password: str) -> bool:
        """
        Verifica contraseña soportando:
        - bcrypt (passlib)
        - pbkdf2:sha256 (legacy werkzeug)

        Si el hash es legacy y el login es correcto,
        migra automáticamente a bcrypt.
        """
        if not self.password_hash or not password:
            return False

        # Intento moderno (bcrypt)
        try:
            if pwd_context.verify(password, self.password_hash):
                return True
        except UnknownHashError:
            pass

        # Fallback legacy (PBKDF2)
        if self.password_hash.startswith("pbkdf2:sha256"):
            if check_password_hash(self.password_hash, password):
                # Migración automática a bcrypt
                self.set_password(password)
                self.force_password_change = True
                db.session.commit()
                return True

        return False

    def __repr__(self):
        return f"<User {self.email}>"
