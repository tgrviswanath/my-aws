"""
cache_patterns.py — Redis caching patterns for production use.
Demonstrates cache-aside, TTL, session storage, and rate limiting.
"""

import json
import os
import time
import uuid
from functools import wraps
from typing import Any, Optional

import redis

REDIS_HOST     = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT     = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")

# Connection pool — reuse connections across requests
pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD or None,
    decode_responses=True,
    max_connections=10,
)

def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=pool)


# ─── Pattern 1: Cache-Aside ───────────────────────────────────────────────────

def cache_aside(key: str, ttl: int = 300):
    """
    Decorator: check cache first, call function on miss, store result.
    Usage: @cache_aside("items:all", ttl=60)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            r = get_redis()
            cached = r.get(key)
            if cached:
                print(f"Cache HIT: {key}")
                return json.loads(cached)

            print(f"Cache MISS: {key}")
            result = func(*args, **kwargs)
            r.setex(key, ttl, json.dumps(result, default=str))
            return result
        return wrapper
    return decorator


def get_or_set(r: redis.Redis, key: str, fetch_fn, ttl: int = 300) -> Any:
    """Manual cache-aside pattern."""
    cached = r.get(key)
    if cached:
        return json.loads(cached), "cache"

    value = fetch_fn()
    r.setex(key, ttl, json.dumps(value, default=str))
    return value, "database"


def invalidate(r: redis.Redis, pattern: str) -> int:
    """Delete all keys matching a pattern."""
    keys = r.keys(pattern)
    if keys:
        return r.delete(*keys)
    return 0


# ─── Pattern 2: Session Storage ───────────────────────────────────────────────

class SessionStore:
    """Store user sessions in Redis with TTL."""

    SESSION_TTL = 3600  # 1 hour

    def __init__(self):
        self.r = get_redis()

    def create(self, user_id: str, data: dict) -> str:
        session_id = str(uuid.uuid4())
        key = f"session:{session_id}"
        self.r.setex(key, self.SESSION_TTL, json.dumps({
            "user_id": user_id,
            "data":    data,
            "created": time.time(),
        }))
        return session_id

    def get(self, session_id: str) -> Optional[dict]:
        key = f"session:{session_id}"
        data = self.r.get(key)
        if not data:
            return None
        # Refresh TTL on access
        self.r.expire(key, self.SESSION_TTL)
        return json.loads(data)

    def delete(self, session_id: str) -> None:
        self.r.delete(f"session:{session_id}")


# ─── Pattern 3: Rate Limiting ─────────────────────────────────────────────────

class RateLimiter:
    """
    Sliding window rate limiter using Redis.
    Allows N requests per window_seconds per identifier.
    """

    def __init__(self, limit: int = 100, window_seconds: int = 60):
        self.limit   = limit
        self.window  = window_seconds
        self.r       = get_redis()

    def is_allowed(self, identifier: str) -> tuple[bool, dict]:
        """
        Returns (allowed: bool, info: dict)
        Uses Redis INCR + EXPIRE for atomic counting.
        """
        key = f"rate_limit:{identifier}:{int(time.time() // self.window)}"

        pipe = self.r.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.window)
        count, _ = pipe.execute()

        remaining = max(0, self.limit - count)
        allowed   = count <= self.limit

        return allowed, {
            "limit":     self.limit,
            "remaining": remaining,
            "reset_in":  self.window - (int(time.time()) % self.window),
            "count":     count,
        }


# ─── Pattern 4: Distributed Lock ─────────────────────────────────────────────

class DistributedLock:
    """
    Redis-based distributed lock (simplified Redlock).
    Prevents concurrent execution of critical sections.
    """

    def __init__(self, name: str, ttl: int = 30):
        self.key   = f"lock:{name}"
        self.ttl   = ttl
        self.token = str(uuid.uuid4())
        self.r     = get_redis()

    def acquire(self) -> bool:
        """Try to acquire the lock. Returns True if acquired."""
        return bool(self.r.set(self.key, self.token, nx=True, ex=self.ttl))

    def release(self) -> None:
        """Release the lock (only if we own it)."""
        # Lua script ensures atomic check-and-delete
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        self.r.eval(script, 1, self.key, self.token)

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError(f"Could not acquire lock: {self.key}")
        return self

    def __exit__(self, *args):
        self.release()
