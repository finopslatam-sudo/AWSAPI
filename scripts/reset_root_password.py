from datetime import datetime, timedelta, timezone

from src.models.database import db
from src.models.client import Client
from app import app


def reset_root_password():
    with app.app_context():
        user = Client.query.filter_by(
            email="contacto@finopslatam.com",
            is_root=True
        ).first()

        if not user:
            print("❌ ROOT no encontrado")
            return

        NEW_PASSWORD = "CAMBIA_ESTA_CLAVE_AHORA"

        user.set_password(NEW_PASSWORD)
        user.force_password_change = True
        user.password_expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
        user.is_active = True

        db.session.commit()

        print("✅ Password ROOT reseteado")
        print("📧 Email:", user.email)
        print("🔐 Password temporal:", NEW_PASSWORD)
        print("⚠️ Debe cambiar la contraseña al ingresar")


if __name__ == "__main__":
    reset_root_password()

