#!/usr/bin/env python3
import sys
import os
from getpass import getpass

# =====================================================
# Asegurar path raíz
# =====================================================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

# =====================================================
# Imports reales del proyecto
# =====================================================
from app import app   # 👈 IMPORTAMOS app, NO create_app
from src.models.database import db
from src.models.client import Client

# =====================================================
# Script reset ROOT
# =====================================================
def main():
    print("\n⚠️  RESET DE PASSWORD USUARIO ROOT ⚠️\n")

    confirm = input("¿Confirmas reset ROOT? (yes): ")
    if confirm.lower() != "yes":
        print("❌ Operación cancelada")
        sys.exit(0)

    with app.app_context():
        root_user = Client.query.filter_by(
            email="contacto@finopslatam.com",
            is_root=True
        ).first()

        if not root_user:
            print("❌ Usuario ROOT no encontrado")
            sys.exit(1)

        password = getpass("Ingresa nueva contraseña ROOT: ")
        confirm_password = getpass("Confirma nueva contraseña ROOT: ")

        if password != confirm_password:
            print("❌ Las contraseñas no coinciden")
            sys.exit(1)

        root_user.set_password(password)
        root_user.force_password_change = False
        root_user.password_expires_at = None
        root_user.is_active = True

        db.session.commit()

        print(f"\n✅ Password ROOT actualizado correctamente ({root_user.email})")

if __name__ == "__main__":
    main()
