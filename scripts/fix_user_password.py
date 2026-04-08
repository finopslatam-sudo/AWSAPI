import os
import sys
from src.config.env_loader import load_environment

# 🔐 Evitar que Flask registre rutas
os.environ["FLASK_SKIP_ROUTES"] = "1"

# Carga ENV desde /etc/finops-api.env (fallback .env en dev)
load_environment()

# 🔧 Validar ENV
if not os.getenv("SQLALCHEMY_DATABASE_URI"):
    raise RuntimeError("❌ SQLALCHEMY_DATABASE_URI no definida")

from app import app, db
from src.auth_system import Client


# -----------------------------
# CONFIGURACIÓN
# -----------------------------
USER_EMAIL = "barbero-mci@finopslatam.com"
NEW_PASSWORD = "Final1234!"


with app.app_context():
    user = Client.query.filter_by(email=USER_EMAIL).first()

    if not user:
        raise RuntimeError("❌ Usuario no encontrado")

    if user.role == "admin":
        raise RuntimeError("⛔ Este script NO se usa para admins")

    # 🔐 LÓGICA CENTRALIZADA (ÚNICA)
    user.set_password(NEW_PASSWORD)

    # 🔒 Seguridad SaaS
    user.is_active = True
    user.force_password_change = True

    db.session.commit()

    print(f"✅ Password reseteado correctamente para {USER_EMAIL}")
