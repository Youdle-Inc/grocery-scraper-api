"""
Async Redis cache helpers for the Grocery Scraper API
"""

import os
import json
import zlib
import hashlib
from typing import Any, Optional

from redis.asyncio import Redis


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
    """Thin async Redis cache wrapper for JSON payloads."""

    def __init__(self, url: Optional[str] = None):
        redis_url = url or os.getenv("REDIS_URL")
        if not redis_url:
            # Lazy: create a dummy client that always misses
            self.client = None
        else:
            self.client = Redis.from_url(redis_url)

    async def get_json(self, key: str) -> Optional[Any]:
        if not self.client:
            return None
        data = await self.client.get(key)
        if data is None:
            return None
        return _decompress_json(data)

    async def set_json(self, key: str, obj: Any, ttl_seconds: int) -> None:
        if not self.client:
            return
        await self.client.set(key, _compress_json(obj), ex=ttl_seconds)

    async def close(self) -> None:
        if self.client:
            await self.client.aclose()

    async def ttl_seconds(self, key: str) -> Optional[int]:
        """Return remaining TTL in seconds, or None if unavailable, -1 if no expiry, -2 if key missing."""
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


