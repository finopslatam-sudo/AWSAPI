import sys
from getpass import getpass
from datetime import datetime

from app import create_app
from src.models.database import db
from src.models.client import Client


ROOT_EMAIL = "contacto@finopslatam.com"


def main():
    
    confirm = input("¿Confirmas reset ROOT? (yes): ")
    if confirm.lower() != "yes":
        print("❌ Operación cancelada por el usuario")
        sys.exit(0)

    app = create_app()

    with app.app_context():
        user = Client.query.filter_by(
            email=ROOT_EMAIL,
            is_root=True
        ).first()

        if not user:
            print("❌ Usuario ROOT no encontrado")
            sys.exit(1)

        print(f"🔐 Reset de password para usuario ROOT: {user.email}")

        password = getpass("Nueva contraseña ROOT: ")
        confirm_password = getpass("Confirmar contraseña ROOT: ")

        if password != confirm_password:
            print("❌ Las contraseñas no coinciden")
            sys.exit(1)

        if len(password) < 10:
            print("❌ La contraseña debe tener al menos 10 caracteres")
            sys.exit(1)

        # 🔒 Actualización segura
        user.set_password(password)
        user.force_password_change = False
        user.password_expires_at = None
        user.is_active = True

        db.session.commit()

        # 🧾 Auditoría básica
        print("✅ Password ROOT actualizada correctamente")
        print(f"📝 [AUDIT] ROOT password reset at {datetime.utcnow().isoformat()} UTC")


if __name__ == "__main__":
    main()
