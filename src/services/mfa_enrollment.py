"""
MFA ENROLLMENT
==============

Alta, baja y regeneración de códigos de recuperación de MFA.
"""

from __future__ import annotations

from datetime import datetime

from src.models.user import User
from src.services.mfa_crypto import (
    build_otpauth_url,
    decrypt_secret,
    encrypt_secret,
    generate_recovery_codes,
    generate_totp_secret,
    hash_recovery_codes,
)
from src.services.mfa_crypto import verify_totp_code as _verify_totp_code


def _utcnow() -> datetime:
    return datetime.utcnow()


def start_totp_enrollment(user: User) -> dict[str, str]:
    secret = generate_totp_secret()
    user.mfa_pending_secret_encrypted = encrypt_secret(secret)
    return {
        "secret": secret,
        "otpauth_url": build_otpauth_url(user, secret),
    }


def finalize_totp_enrollment(user: User, code: str) -> list[str]:
    pending_secret = decrypt_secret(user.mfa_pending_secret_encrypted)
    if not pending_secret:
        raise ValueError("mfa_setup_not_started")

    if not _verify_totp_code(pending_secret, code):
        raise ValueError("invalid_mfa_code")

    recovery_codes = generate_recovery_codes()
    user.mfa_enabled = True
    user.mfa_secret_encrypted = encrypt_secret(pending_secret)
    user.mfa_pending_secret_encrypted = None
    user.mfa_confirmed_at = _utcnow()
    user.mfa_last_used_at = _utcnow()
    user.mfa_failed_attempts = 0
    user.mfa_locked_until = None
    user.mfa_recovery_codes_hash = hash_recovery_codes(recovery_codes)
    return recovery_codes


def disable_mfa(user: User) -> None:
    user.mfa_enabled = False
    user.mfa_secret_encrypted = None
    user.mfa_pending_secret_encrypted = None
    user.mfa_confirmed_at = None
    user.mfa_recovery_codes_hash = None
    user.mfa_last_used_at = None
    user.mfa_failed_attempts = 0
    user.mfa_locked_until = None


def regenerate_recovery_codes(user: User) -> list[str]:
    codes = generate_recovery_codes()
    user.mfa_recovery_codes_hash = hash_recovery_codes(codes)
    return codes
