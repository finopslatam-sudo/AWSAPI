import os

# 🔐 Evitar que Flask registre rutas
os.environ["FLASK_SKIP_ROUTES"] = "1"

# 🔧 Validar ENV
if not os.getenv("SQLALCHEMY_DATABASE_URI"):
    raise RuntimeError("❌ SQLALCHEMY_DATABASE_URI no definida")

from app import app, db
from src.auth_system import Client

ADMIN_EMAIL = "adminroot@finopslatam.com"
NEW_PASSWORD = "Adminroot1234!"

with app.app_context():
    client = Client.query.filter_by(email=ADMIN_EMAIL).first()

    if not client:
        raise RuntimeError("❌ Usuario admin no encontrado")

    # ✅ Reset de password (bcrypt correcto)
    client.set_password(NEW_PASSWORD)

    # 🔐 Estado seguro para producción
    client.is_active = True
    client.force_password_change = False  # 🔥 CLAVE

    db.session.commit()

    print("✅ Password del admin reseteado correctamente (login permitido)")
