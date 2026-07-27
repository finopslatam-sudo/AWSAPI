"""
MFA VERIFICATION
================

Verificación de código TOTP / código de recuperación en el momento
del login, y control de bloqueo temporal por intentos fallidos.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

from src.models.user import User, pwd_context
from src.services.mfa_crypto import decrypt_secret, verify_totp_code


def _utcnow() -> datetime:
    return datetime.utcnow()


def verify_recovery_code(user: User, code: str) -> bool:
    raw = user.mfa_recovery_codes_hash
    if not raw:
        return False

    try:
        hashes = json.loads(raw)
    except json.JSONDecodeError:
        return False

    normalized = str(code or "").strip().upper()
    if not normalized:
        return False

    remaining_hashes = []
    matched = False

    for item in hashes:
        if not matched and pwd_context.verify(normalized, item):
            matched = True
            continue
        remaining_hashes.append(item)

    if matched:
        user.mfa_recovery_codes_hash = json.dumps(remaining_hashes)
    return matched


def is_mfa_temporarily_locked(user: User) -> bool:
    return bool(user.mfa_locked_until and user.mfa_locked_until > _utcnow())


def register_mfa_failure(user: User) -> None:
    user.mfa_failed_attempts = (user.mfa_failed_attempts or 0) + 1
    max_attempts = int(os.getenv("MFA_MAX_FAILED_ATTEMPTS", "5"))
    lock_minutes = int(os.getenv("MFA_LOCK_MINUTES", "10"))

    if user.mfa_failed_attempts >= max_attempts:
        user.mfa_locked_until = _utcnow() + timedelta(minutes=lock_minutes)
        user.mfa_failed_attempts = 0


def register_mfa_success(user: User) -> None:
    user.mfa_failed_attempts = 0
    user.mfa_locked_until = None
    user.mfa_last_used_at = _utcnow()


def verify_user_totp(user: User, code: str) -> bool:
    secret = decrypt_secret(user.mfa_secret_encrypted)
    if not secret:
        return False
    return verify_totp_code(secret, code)
