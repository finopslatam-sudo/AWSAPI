"""
HTTP hardening helpers for FinOpsLatam API.

Includes:
- Client IP extraction
- Host header allowlist validation
- In-memory sliding-window rate limiting
- Basic security response headers
"""

from __future__ import annotations

import os
import time
import threading
from collections import defaultdict, deque
from typing import Deque

from flask import request


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def get_client_ip() -> str:
    """
    Best-effort client IP extraction.
    Trusts proxy headers only if TRUST_PROXY_HEADERS=true (default true in prod setups).
    """
    trust_proxy = _env_bool("TRUST_PROXY_HEADERS", True)

    if trust_proxy:
        xff = request.headers.get("X-Forwarded-For", "")
        if xff:
            candidate = xff.split(",")[0].strip()
            if candidate:
                return candidate

        xri = request.headers.get("X-Real-IP", "").strip()
        if xri:
            return xri

    return (request.remote_addr or "unknown").strip() or "unknown"


def is_allowed_host() -> bool:
    """
    Optional host header validation to reduce host header attacks.
    Enable via ENFORCE_ALLOWED_HOSTS=true.
    """
    enforce = _env_bool("ENFORCE_ALLOWED_HOSTS", False)
    if not enforce:
        return True

    raw_hosts = os.getenv(
        "ALLOWED_HOSTS",
        "api.finopslatam.com,localhost,127.0.0.1",
    )
    allowed = {h.strip().lower() for h in raw_hosts.split(",") if h.strip()}

    host = (request.host or "").split(":", 1)[0].strip().lower()
    return host in allowed


def apply_security_headers(response):
    """
    Applies conservative security headers at API level.
    """
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("X-XSS-Protection", "0")
    return response


class SlidingWindowRateLimiter:
    """
    In-memory sliding-window limiter.

    NOTE: this protects each API process independently. For distributed deployments,
    add network-level controls (WAF/CDN/load balancer) for full protection.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: dict[str, Deque[float]] = defaultdict(deque)

    @staticmethod
    def _prune(events: Deque[float], window_seconds: int, now: float) -> None:
        cutoff = now - window_seconds
        while events and events[0] <= cutoff:
            events.popleft()

    def count(self, key: str, window_seconds: int) -> int:
        now = time.time()
        with self._lock:
            bucket = self._events[key]
            self._prune(bucket, window_seconds, now)
            return len(bucket)

    def add(self, key: str) -> None:
        now = time.time()
        with self._lock:
            self._events[key].append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)

    def hit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """
        Registers a hit and returns (allowed, retry_after_seconds).
        """
        now = time.time()
        with self._lock:
            bucket = self._events[key]
            self._prune(bucket, window_seconds, now)

            if len(bucket) >= limit:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                return False, retry_after

            bucket.append(now)
            return True, 0


# Shared process-level limiter instance
rate_limiter = SlidingWindowRateLimiter()
