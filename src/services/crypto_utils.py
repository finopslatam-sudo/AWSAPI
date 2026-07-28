"""
CRYPTO UTILS
============
Derivación de clave Fernet compartida, reutilizada por el cifrado de
secretos MFA (mfa_crypto.py) y el cifrado en reposo de role_arn/external_id
(models/encrypted_types.py). Misma lógica de fallback de env vars que ya
usaba mfa_crypto.py._load_secret_material().
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet


def _load_key_material(primary_env: str, fallback_env: str) -> str:
    material = os.getenv(primary_env) or os.getenv(fallback_env) or ""
    if not material:
        raise RuntimeError(f"{primary_env} o {fallback_env} es requerido")
    return material


def derive_fernet_key(*, primary_env: str, fallback_env: str = "JWT_SECRET_KEY") -> bytes:
    material = _load_key_material(primary_env, fallback_env)
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet(*, primary_env: str, fallback_env: str = "JWT_SECRET_KEY") -> Fernet:
    return Fernet(derive_fernet_key(primary_env=primary_env, fallback_env=fallback_env))
