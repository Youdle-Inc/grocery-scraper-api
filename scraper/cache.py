"""
Async Redis cache helpers for the Grocery Scraper API
Supports both Redis and in-memory caching
"""

import os
import json
import zlib
import hashlib
import time
from typing import Any, Optional, Dict, Tuple

try:
    from redis.asyncio import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


def _normalize_query(query: str) -> str:
    return " ".join(query.lower().strip().split())


def sha1_hex(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def _compress_json(obj: Any) -> bytes:
    return zlib.compress(
        json.dumps(obj, separators=(",", ":")).encode("utf-8"), level=6
    )


def _decompress_json(blob: bytes) -> Any:
    return json.loads(zlib.decompress(blob).decode("utf-8"))


class Cache:
    """
    Async cache wrapper supporting both Redis and in-memory storage.
    Falls back to in-memory if Redis is not available.
    """

    def __init__(self, url: Optional[str] = None):
        redis_url = url or os.getenv("REDIS_URL")
        self.client = None
        self.use_memory = False
        self._memory_cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expiry_time)

        if redis_url and REDIS_AVAILABLE:
            try:
                self.client = Redis.from_url(redis_url)
            except Exception:
                self.use_memory = True
        else:
            # Use in-memory cache as fallback
            self.use_memory = True

    def _clean_expired(self):
        """Remove expired entries from memory cache"""
        now = time.time()
        expired_keys = [k for k, (_, exp) in self._memory_cache.items() if exp < now]
        for k in expired_keys:
            del self._memory_cache[k]

    async def get_json(self, key: str) -> Optional[Any]:
        if self.use_memory:
            self._clean_expired()
            if key in self._memory_cache:
                value, expiry = self._memory_cache[key]
                if expiry > time.time():
                    return value
                else:
                    del self._memory_cache[key]
            return None

        if not self.client:
            return None
        data = await self.client.get(key)
        if data is None:
            return None
        return _decompress_json(data)

    async def set_json(self, key: str, obj: Any, ttl_seconds: int) -> None:
        if self.use_memory:
            expiry = time.time() + ttl_seconds
            self._memory_cache[key] = (obj, expiry)
            # Limit memory cache size to 1000 entries
            if len(self._memory_cache) > 1000:
                self._clean_expired()
            return

        if not self.client:
            return
        await self.client.set(key, _compress_json(obj), ex=ttl_seconds)

    async def close(self) -> None:
        if self.client:
            await self.client.aclose()

    async def ttl_seconds(self, key: str) -> Optional[int]:
        """Return remaining TTL in seconds, or None if unavailable, -1 if no expiry, -2 if key missing."""
        if self.use_memory:
            if key in self._memory_cache:
                _, expiry = self._memory_cache[key]
                remaining = int(expiry - time.time())
                return remaining if remaining > 0 else -2
            return -2

        if not self.client:
            return None
        return await self.client.ttl(key)


# Key helpers
def stores_key(zipcode: str) -> str:
    return f"stores:zip:{zipcode}"


def products_key(zipcode: str, query: str, store_ids_sorted: list[str], enhance: bool) -> str:
    normalized_query = _normalize_query(query)
    qhash = sha1_hex(normalized_query)
    set_hash = sha1_hex(
        ",".join(sorted(store_ids_sorted)) if store_ids_sorted else "__none__"
    )
    return f"products:zip:{zipcode}:q:{qhash}:stores:{set_hash}:enh:{1 if enhance else 0}"


def raw_source_key(zipcode: str, store_id: str, query: str, source: str) -> str:
    normalized_query = _normalize_query(query)
    qhash = sha1_hex(normalized_query)
    return f"raw:zip:{zipcode}:store:{store_id}:q:{qhash}:src:{source}"


