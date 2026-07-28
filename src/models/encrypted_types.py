"""
ENCRYPTED TYPES
===============
TypeDecorator de SQLAlchemy para cifrar columnas de texto en reposo de
forma transparente (Fernet): el código que lee/escribe el modelo sigue
viendo texto plano en Python, solo lo guardado en la BD queda cifrado.
"""

from __future__ import annotations

from cryptography.fernet import InvalidToken
from sqlalchemy.types import TypeDecorator, String

from src.services.crypto_utils import get_fernet


class EncryptedString(TypeDecorator):
    """Columna String cifrada con Fernet. Tolerante a filas todavía en
    texto plano (no migradas): si el descifrado falla, devuelve el valor
    crudo en vez de romper la lectura."""

    impl = String
    cache_ok = True

    def __init__(self, *args, env_var: str = "AWS_SECRET_ENCRYPTION_KEY", **kwargs):
        self._env_var = env_var
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        fernet = get_fernet(primary_env=self._env_var)
        return fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        fernet = get_fernet(primary_env=self._env_var)
        try:
            return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            return value
