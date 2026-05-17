"""
Redis caching service for the AI Incubator.
Provides: response caching, session store, and rate limit backing store.
Falls back gracefully when Redis is unavailable.
"""

import json
import hashlib
import structlog
from typing import Any, Optional

logger = structlog.get_logger()

# Try to import redis — graceful fallback if not installed
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheService:
    """Async Redis cache with automatic JSON serialization."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self._client: Optional[Any] = None
        self._url = redis_url
        self._connected = False

    async def connect(self):
        if not REDIS_AVAILABLE:
            logger.warning("Redis not installed — caching disabled")
            return

        try:
            self._client = aioredis.from_url(self._url, decode_responses=True)
            await self._client.ping()
            self._connected = True
            logger.info("Redis connected", url=self._url)
        except Exception as e:
            logger.warning("Redis connection failed — caching disabled", error=str(e))
            self._connected = False

    async def disconnect(self):
        if self._client and self._connected:
            await self._client.aclose()
            self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Basic Operations ─────────────────────────────────────────

    async def get(self, key: str) -> Optional[Any]:
        if not self._connected:
            return None
        try:
            value = await self._client.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        if not self._connected:
            return False
        try:
            await self._client.setex(key, ttl_seconds, json.dumps(value, default=str))
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        if not self._connected:
            return False
        try:
            await self._client.delete(key)
            return True
        except Exception:
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching a glob pattern."""
        if not self._connected:
            return 0
        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await self._client.delete(*keys)
            return len(keys)
        except Exception:
            return 0

    # ── Cache Helpers ────────────────────────────────────────────

    def make_key(self, prefix: str, *parts: str) -> str:
        """Create a namespaced cache key."""
        raw = ":".join([prefix] + list(parts))
        return f"incubator:{raw}"

    def hash_key(self, prefix: str, data: dict) -> str:
        """Create a hash-based cache key for query parameters."""
        h = hashlib.md5(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:12]
        return f"incubator:{prefix}:{h}"

    # ── Workflow Cache ───────────────────────────────────────────

    async def cache_agent_result(self, idea_id: str, agent_role: str, result: dict, ttl: int = 3600):
        key = self.make_key("agent_result", idea_id, agent_role)
        return await self.set(key, result, ttl)

    async def get_agent_result(self, idea_id: str, agent_role: str) -> Optional[dict]:
        key = self.make_key("agent_result", idea_id, agent_role)
        return await self.get(key)

    async def cache_workflow_state(self, idea_id: str, state: dict, ttl: int = 1800):
        key = self.make_key("workflow", idea_id)
        return await self.set(key, state, ttl)

    async def get_workflow_state(self, idea_id: str) -> Optional[dict]:
        key = self.make_key("workflow", idea_id)
        return await self.get(key)

    async def invalidate_idea_cache(self, idea_id: str):
        """Clear all cached data for an idea."""
        return await self.invalidate_pattern(f"incubator:*:{idea_id}:*")


# ── Singleton ────────────────────────────────────────────────────
_cache: Optional[CacheService] = None


def get_cache() -> CacheService:
    global _cache
    if _cache is None:
        from app.config import get_settings
        settings = get_settings()
        _cache = CacheService(getattr(settings, "redis_url", "redis://localhost:6379/0"))
    return _cache
