#!/usr/bin/env python3
import sys
import os
from getpass import getpass

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv("/etc/finops-api.env")  # 🔴 CLAVE

from app import app
from src.models.database import db
from src.models.client import Client

def main():
    print("\n⚠️  RESET DE PASSWORD USUARIO ROOT ⚠️\n")

    if input("¿Confirmas reset ROOT? (yes): ").lower() != "yes":
        sys.exit(0)

    email = "contacto@finopslatam.com"

    with app.app_context():
        user = Client.query.filter_by(email=email, is_root=True).first()

        if not user:
            print("❌ Usuario ROOT no encontrado")
            sys.exit(1)

        pwd1 = getpass("Nueva contraseña ROOT: ")
        pwd2 = getpass("Confirma contraseña: ")

        if pwd1 != pwd2:
            print("❌ Las contraseñas no coinciden")
            sys.exit(1)

        user.set_password(pwd1)
        user.force_password_change = False   # 🔴 IMPORTANTE
        user.is_active = True

        db.session.commit()

        print("✅ Password ROOT actualizado correctamente")

if __name__ == "__main__":
    main()
