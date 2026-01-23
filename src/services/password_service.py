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

DEFAULT_TEMP_PASSWORD_LENGTH = 10


def generate_temp_password(length: int = DEFAULT_TEMP_PASSWORD_LENGTH) -> str:
    """
    Genera una contraseña temporal segura.

    Args:
        length (int): longitud del password (mínimo recomendado: 10)

    Returns:
        str: contraseña temporal
    """
    if length < 8:
        raise ValueError("La longitud mínima del password temporal es 8")

    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))
