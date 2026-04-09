"""
MFA SERVICE
===========

Servicio para gestionar MFA basado en TOTP y códigos de recuperación.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import time
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote

from cryptography.fernet import Fernet, InvalidToken

from src.models.client import Client
from src.models.user import User, pwd_context


SYSTEM_MFA_ROLES = {"root", "admin"}
CLIENT_ADMIN_ROLES = {"owner", "finops_admin"}


def _utcnow() -> datetime:
    return datetime.utcnow()


def _load_secret_material() -> str:
    secret = (
        os.getenv("MFA_SECRET_ENCRYPTION_KEY")
        or os.getenv("JWT_SECRET_KEY")
        or ""
    )
    if not secret:
        raise RuntimeError("MFA_SECRET_ENCRYPTION_KEY o JWT_SECRET_KEY es requerido")
    return secret


def _build_fernet() -> Fernet:
    digest = hashlib.sha256(_load_secret_material().encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _normalize_base32(secret: str) -> str:
    clean = "".join(secret.strip().split()).upper()
    padding = "=" * (-len(clean) % 8)
    return clean + padding


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("utf-8").rstrip("=")


def build_otpauth_url(user: User, secret: str) -> str:
    issuer = os.getenv("MFA_ISSUER_NAME", "FinOpsLatam")
    label = quote(f"{issuer}:{user.email}")
    issuer_quoted = quote(issuer)
    return (
        f"otpauth://totp/{label}"
        f"?secret={secret}&issuer={issuer_quoted}&algorithm=SHA1&digits=6&period=30"
    )


def _hotp(secret: str, counter: int, digits: int = 6) -> str:
    key = base64.b32decode(_normalize_base32(secret), casefold=True)
    message = struct.pack(">Q", counter)
    digest = hmac.new(key, message, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (
        ((digest[offset] & 0x7F) << 24)
        | ((digest[offset + 1] & 0xFF) << 16)
        | ((digest[offset + 2] & 0xFF) << 8)
        | (digest[offset + 3] & 0xFF)
    )
    return str(code % (10 ** digits)).zfill(digits)


def verify_totp_code(secret: str, code: str, *, window: int = 1, step: int = 30) -> bool:
    normalized = "".join(ch for ch in str(code) if ch.isdigit())
    if len(normalized) != 6:
        return False

    counter = int(time.time() // step)
    for offset in range(-window, window + 1):
        if hmac.compare_digest(_hotp(secret, counter + offset), normalized):
            return True
    return False


def encrypt_secret(raw_secret: str) -> str:
    return _build_fernet().encrypt(raw_secret.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return _build_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None


def generate_recovery_codes(total: int = 8) -> list[str]:
    return [
        f"{secrets.token_hex(2)}-{secrets.token_hex(2)}".upper()
        for _ in range(total)
    ]


def hash_recovery_codes(codes: list[str]) -> str:
    return json.dumps([pwd_context.hash(code) for code in codes])


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


def issue_login_challenge(user: User) -> str:
    payload = {
        "user_id": user.id,
        "email": user.email,
        "client_id": user.client_id,
        "iat": int(time.time()),
    }
    encoded_payload = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("utf-8").rstrip("=")
    signature = hmac.new(
        _load_secret_material().encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{encoded_payload}.{encoded_signature}"


def parse_login_challenge(token: str, *, max_age_seconds: int | None = None) -> dict[str, Any]:
    ttl = max_age_seconds or int(os.getenv("MFA_CHALLENGE_TTL_SECONDS", "300"))

    try:
        encoded_payload, encoded_signature = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("challenge_invalid") from exc

    expected_signature = hmac.new(
        _load_secret_material().encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    actual_signature = base64.urlsafe_b64decode(
        encoded_signature + ("=" * (-len(encoded_signature) % 4))
    )

    if not hmac.compare_digest(expected_signature, actual_signature):
        raise ValueError("challenge_invalid")

    try:
        raw_payload = base64.urlsafe_b64decode(
            encoded_payload + ("=" * (-len(encoded_payload) % 4))
        ).decode("utf-8")
        data = json.loads(raw_payload)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError("challenge_invalid") from exc

    if not isinstance(data, dict) or "user_id" not in data:
        raise ValueError("challenge_invalid")

    issued_at = int(data.get("iat", 0))
    if not issued_at or int(time.time()) - issued_at > ttl:
        raise ValueError("challenge_expired")

    return data


def get_client_mfa_policy(user: User) -> str:
    if user.global_role in SYSTEM_MFA_ROLES:
        return "required"

    if not user.client_id:
        return "disabled"

    client = Client.query.get(user.client_id)
    if not client or not client.is_active:
        return "disabled"

    if client.mfa_policy in Client.MFA_POLICIES:
        return client.mfa_policy

    return "disabled"


def is_mfa_required_for_user(user: User) -> bool:
    policy = get_client_mfa_policy(user)

    if policy == "required":
        return True

    if policy == "required_for_admins":
        return user.client_role in CLIENT_ADMIN_ROLES or bool(user.mfa_enabled)

    if policy == "optional":
        return bool(user.mfa_enabled)

    return False


def must_enroll_mfa(user: User) -> bool:
    policy = get_client_mfa_policy(user)

    if user.global_role in SYSTEM_MFA_ROLES:
        return not user.mfa_enabled

    if policy == "required":
        return not user.mfa_enabled

    if policy == "required_for_admins" and user.client_role in CLIENT_ADMIN_ROLES:
        return not user.mfa_enabled

    return False


def can_disable_mfa(user: User) -> bool:
    policy = get_client_mfa_policy(user)

    if user.global_role in SYSTEM_MFA_ROLES:
        return False

    if policy == "required":
        return False

    if policy == "required_for_admins" and user.client_role in CLIENT_ADMIN_ROLES:
        return False

    return True


def get_mfa_status(user: User) -> dict[str, Any]:
    policy = get_client_mfa_policy(user)
    return {
        "policy": policy,
        "enabled": bool(user.mfa_enabled),
        "required_now": is_mfa_required_for_user(user) or must_enroll_mfa(user),
        "can_disable": can_disable_mfa(user),
        "has_recovery_codes": bool(user.mfa_recovery_codes_hash),
        "confirmed_at": (
            user.mfa_confirmed_at.isoformat()
            if user.mfa_confirmed_at else None
        ),
        "last_used_at": (
            user.mfa_last_used_at.isoformat()
            if user.mfa_last_used_at else None
        ),
    }


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

    if not verify_totp_code(pending_secret, code):
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
