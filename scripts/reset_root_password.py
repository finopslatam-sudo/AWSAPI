#!/usr/bin/env python3
import sys
from getpass import getpass

from app import create_app
from src.models.database import db
from src.models.client import Client


def main():
    print("\n⚠️  RESET DE PASSWORD USUARIO ROOT ⚠️\n")

    confirm = input("¿Confirmas reset ROOT? (yes): ")
    if confirm.lower() != "yes":
        print("❌ Operación cancelada.")
        sys.exit(0)

    email = "contacto@finopslatam.com"
    new_password = getpass("Ingresa nueva contraseña ROOT: ")
    confirm_password = getpass("Confirma nueva contraseña ROOT: ")

    if new_password != confirm_password:
        print("❌ Las contraseñas no coinciden.")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        user = Client.query.filter_by(email=email, is_root=True).first()

        if not user:
            print("❌ Usuario ROOT no encontrado.")
            sys.exit(1)

        user.set_password(new_password)
        user.force_password_change = False
        user.password_expires_at = None
        user.is_active = True

        db.session.commit()

        print(f"✅ Password ROOT actualizado correctamente ({email})")


if __name__ == "__main__":
    main()
