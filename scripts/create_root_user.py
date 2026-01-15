import sys
import os
from datetime import datetime, timedelta

# ⬅️ AÑADIR RAÍZ DEL PROYECTO AL PYTHONPATH
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from app import app
from src.models.database import db
from src.models.client import Client


def create_root_user():
    with app.app_context():
        existing_root = Client.query.filter_by(is_root=True).first()

        if existing_root:
            print("❌ ROOT ya existe:", existing_root.email)
            return

        root = Client(
            company_name="FinOpsLatam",
            email="contacto@finopslatam.com",
            contact_name="Root User",
            role="admin",
            is_root=True,
            is_active=True,

            # 🔐 Seguridad
            force_password_change=True,
            password_expires_at=datetime.utcnow() + timedelta(minutes=30),

            created_at=datetime.utcnow()
        )

        # ⚠️ Password temporal
        root.set_password("PASSWORD")

        db.session.add(root)
        db.session.commit()

        print("✅ ROOT creado correctamente")
        print("📧 Email:", root.email)
        print("⚠️ Debe cambiar la contraseña en el primer login")


if __name__ == "__main__":
    create_root_user()
