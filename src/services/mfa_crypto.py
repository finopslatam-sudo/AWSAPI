"""
MFA CRYPTO
==========

Primitivas de cifrado/firma para el secreto TOTP y los challenge
tokens de login. Cifrado por stream (HMAC-SHA256 keystream) + firma
HMAC — no es AES-GCM/Fernet de una librería estándar, pero mantiene
exactamente el mismo formato ("v1.<nonce>.<ciphertext>.<sig>") que ya
existe en producción, así que descifra los secretos ya guardados.
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
from typing import Any
from urllib.parse import quote

from src.models.user import User


def _load_secret_material() -> str:
    secret = (
        os.getenv("MFA_SECRET_ENCRYPTION_KEY")
        or os.getenv("JWT_SECRET_KEY")
        or ""
    )
    if not secret:
        raise RuntimeError("MFA_SECRET_ENCRYPTION_KEY o JWT_SECRET_KEY es requerido")
    return secret


def _urlsafe_b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _urlsafe_b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + ("=" * (-len(value) % 4)))


def _keystream(secret: bytes, nonce: bytes, length: int) -> bytes:
    output = bytearray()
    counter = 0

    while len(output) < length:
        block = hmac.new(
            secret,
            nonce + counter.to_bytes(4, "big"),
            hashlib.sha256,
        ).digest()
        output.extend(block)
        counter += 1

    return bytes(output[:length])


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
    secret_key = hashlib.sha256(_load_secret_material().encode("utf-8")).digest()
    nonce = secrets.token_bytes(16)
    plaintext = raw_secret.encode("utf-8")
    stream = _keystream(secret_key, nonce, len(plaintext))
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, stream))
    signature = hmac.new(secret_key, nonce + ciphertext, hashlib.sha256).digest()
    return ".".join([
        "v1",
        _urlsafe_b64encode(nonce),
        _urlsafe_b64encode(ciphertext),
        _urlsafe_b64encode(signature),
    ])


def decrypt_secret(token: str | None) -> str | None:
    if not token:
        return None

    try:
        version, encoded_nonce, encoded_ciphertext, encoded_signature = token.split(".", 3)
        if version != "v1":
            return None

        secret_key = hashlib.sha256(_load_secret_material().encode("utf-8")).digest()
        nonce = _urlsafe_b64decode(encoded_nonce)
        ciphertext = _urlsafe_b64decode(encoded_ciphertext)
        signature = _urlsafe_b64decode(encoded_signature)
        expected_signature = hmac.new(
            secret_key,
            nonce + ciphertext,
            hashlib.sha256,
        ).digest()

        if not hmac.compare_digest(signature, expected_signature):
            return None

        stream = _keystream(secret_key, nonce, len(ciphertext))
        plaintext = bytes(a ^ b for a, b in zip(ciphertext, stream))
        return plaintext.decode("utf-8")
    except (ValueError, TypeError):
        return None


def generate_recovery_codes(total: int = 8) -> list[str]:
    return [
        f"{secrets.token_hex(2)}-{secrets.token_hex(2)}".upper()
        for _ in range(total)
    ]


def hash_recovery_codes(codes: list[str]) -> str:
    from src.models.user import pwd_context
    return json.dumps([pwd_context.hash(code) for code in codes])


def issue_login_challenge(user: User) -> str:
    payload = {
        "user_id": user.id,
        "email": user.email,
        "client_id": user.client_id,
        "iat": int(time.time()),
    }
    encoded_payload = _urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = hmac.new(
        _load_secret_material().encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    encoded_signature = _urlsafe_b64encode(signature)
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
    actual_signature = _urlsafe_b64decode(encoded_signature)

    if not hmac.compare_digest(expected_signature, actual_signature):
        raise ValueError("challenge_invalid")

    try:
        raw_payload = _urlsafe_b64decode(encoded_payload).decode("utf-8")
        data = json.loads(raw_payload)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError("challenge_invalid") from exc

    if not isinstance(data, dict) or "user_id" not in data:
        raise ValueError("challenge_invalid")

    issued_at = int(data.get("iat", 0))
    if not issued_at or int(time.time()) - issued_at > ttl:
        raise ValueError("challenge_expired")

    return data
