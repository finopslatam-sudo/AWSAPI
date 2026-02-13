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

TEMP_PASSWORD_EXPIRATION_MINUTES = 30


def get_temp_password_expiration():
    """
    Retorna timestamp de expiración para password temporal
    en zona horaria America/Santiago.
    """
    now = datetime.now(ZoneInfo("America/Santiago"))
    return now + timedelta(minutes=TEMP_PASSWORD_EXPIRATION_MINUTES)

