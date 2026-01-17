#!/usr/bin/env python3
import sys
import os
from getpass import getpass

# =========================
# Bootstrap path correcto
# =========================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

# =========================
# ⚠️ NO cargamos .env
# Usamos el mismo entorno
# que systemd / gunicorn
# =========================

from app import app
from src.models.database import db
from src.models.client import Client


def main():
    print("\n⚠️  RESET DE PASSWORD USUARIO ROOT ⚠️\n")

    confirm = input("¿Confirmas reset ROOT? (yes): ")
    if confirm.lower() != "yes":
        print("❌ Operación cancelada")
        sys.exit(0)

    email = os.getenv("ROOT_EMAIL", "contacto@finopslatam.com")

    with app.app_context():
        user = Client.query.filter_by(
            email=email,
            is_root=True
        ).first()

        if not user:
            print("❌ Usuario ROOT no encontrado")
            sys.exit(1)

        new_password = getpass("Nueva contraseña ROOT: ")
        confirm_password = getpass("Confirma contraseña: ")

        if new_password != confirm_password:
            print("❌ Las contraseñas no coinciden")
            sys.exit(1)

        try:
            user.set_password(new_password)
            user.force_password_change = True
            user.password_expires_at = None
            user.is_active = True

            db.session.commit()

            print("\n✅ Password ROOT actualizado correctamente")
            print("🔐 El usuario deberá cambiar la contraseña al iniciar sesión\n")

        except Exception as e:
            db.session.rollback()
            print("❌ Error al actualizar la contraseña:")
            print(e)
            sys.exit(1)


if __name__ == "__main__":
    main()
