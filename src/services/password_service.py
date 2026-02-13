"""
PASSWORD SERVICE
================

Servicio centralizado para generación de contraseñas temporales.

Uso:
- Reset de contraseña
- Creación inicial de usuarios
- Flujos de recuperación (forgot password)

Notas:
- Usa generador criptográficamente seguro (secrets)
- Las contraseñas generadas son TEMPORALES
- La complejidad final la define el usuario al cambiarla
"""

import secrets
import string
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


DEFAULT_TEMP_PASSWORD_LENGTH = 10
TEMP_PASSWORD_EXPIRATION_MINUTES = 30

def generate_temp_password(length: int = DEFAULT_TEMP_PASSWORD_LENGTH) -> str:
    if length < 8:
        raise ValueError("La longitud mínima del password temporal es 8")

    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))

def get_temp_password_expiration():
    """
    Retorna timestamp de expiración para password temporal
    en zona horaria America/Santiago.
    """
    now = datetime.now(ZoneInfo("America/Santiago"))
    return now + timedelta(minutes=TEMP_PASSWORD_EXPIRATION_MINUTES)

