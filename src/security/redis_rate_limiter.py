"""
Redis-backed sliding-window rate limiter.

Same public surface as SlidingWindowRateLimiter (count/add/reset/hit) so
callers (config/security_middleware.py, auth/routes.py) need no changes —
only the underlying storage swaps from in-memory to Redis sorted sets.
"""

from __future__ import annotations

import time
import uuid


class RedisSlidingWindowRateLimiter:

    def __init__(self, redis_client) -> None:
        self._redis = redis_client

    def count(self, key: str, window_seconds: int) -> int:
        now = time.time()
        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, now - window_seconds)
        pipe.zcard(key)
        _, count = pipe.execute()
        return count

    def add(self, key: str) -> None:
        now = time.time()
        self._redis.zadd(key, {f"{now}:{uuid.uuid4().hex}": now})

    def reset(self, key: str) -> None:
        self._redis.delete(key)

    def hit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, now - window_seconds)
        pipe.zcard(key)
        _, count = pipe.execute()

        if count >= limit:
            oldest = self._redis.zrange(key, 0, 0, withscores=True)
            oldest_ts = oldest[0][1] if oldest else now
            retry_after = max(1, int(window_seconds - (now - oldest_ts)))
            return False, retry_after

        self._redis.zadd(key, {f"{now}:{uuid.uuid4().hex}": now})
        self._redis.expire(key, window_seconds)
        return True, 0
