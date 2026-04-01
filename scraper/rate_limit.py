"""
IP-based rate limiting helpers for FastAPI routes.

Supports a Redis-backed sliding window for request starts and an active-stream
counter for long-lived streaming endpoints. Falls back to in-memory storage
when Redis is not configured.
"""

from __future__ import annotations

import asyncio
import math
import os
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover - dependency is installed in prod
    Redis = None


@dataclass(frozen=True)
class RouteLimit:
    request_limit: int
    window_seconds: int
    concurrent_stream_limit: Optional[int] = None
    concurrent_retry_after_seconds: int = 5
    active_ttl_seconds: int = 600


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int
    limit: int
    remaining: int


DEFAULT_ROUTE_LIMITS: Dict[str, RouteLimit] = {
    "search": RouteLimit(request_limit=30, window_seconds=60),
    "aggregate": RouteLimit(request_limit=10, window_seconds=60),
    "stores": RouteLimit(request_limit=20, window_seconds=60),
    "search_stream": RouteLimit(
        request_limit=5,
        window_seconds=60,
        concurrent_stream_limit=2,
        concurrent_retry_after_seconds=5,
        active_ttl_seconds=600,
    ),
    "aggregate_stream": RouteLimit(
        request_limit=10,
        window_seconds=60,
        concurrent_stream_limit=5,
        concurrent_retry_after_seconds=5,
        active_ttl_seconds=600,
    ),
}

EXEMPT_PATHS = {
    "/",
    "/api",
    "/health",
    "/swagger",
    "/openapi.json",
    "/docs",
    "/redoc",
}


def normalize_path(path: str) -> str:
    normalized = path.rstrip("/")
    return normalized or "/"


def resolve_route_key(path: str) -> Optional[str]:
    normalized = normalize_path(path)
    if normalized in EXEMPT_PATHS:
        return None
    if normalized.startswith("/stores/"):
        return "stores"
    if normalized == "/products/search":
        return "search"
    if normalized == "/products/aggregate":
        return "aggregate"
    if normalized == "/products/search/stream":
        return "search_stream"
    if normalized == "/products/aggregate/stream":
        return "aggregate_stream"
    return None


def get_client_ip(request) -> str:
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        for candidate in x_forwarded_for.split(","):
            ip = candidate.strip()
            if ip:
                return ip

    client = getattr(request, "client", None)
    if client and getattr(client, "host", None):
        return client.host

    return "unknown"


class RateLimiter:
    """
    Route-aware limiter with request window limiting and active-stream caps.

    Redis is preferred when available. In-memory fallback is best-effort and
    only protects a single process.
    """

    _REQUEST_WINDOW_TTL_BUFFER_SECONDS = 60

    def __init__(
        self,
        redis_url: Optional[str] = None,
        policies: Optional[Dict[str, RouteLimit]] = None,
    ):
        self.policies = policies or DEFAULT_ROUTE_LIMITS
        self._use_memory = True
        self._redis = None

        if redis_url is None:
            redis_url = os.getenv("REDIS_URL")

        if redis_url and Redis is not None:
            try:
                self._redis = Redis.from_url(redis_url)
                self._use_memory = False
            except Exception:
                self._redis = None
                self._use_memory = True

        self._request_events: Dict[str, Deque[float]] = defaultdict(deque)
        self._active_stream_counts: Dict[str, int] = defaultdict(int)
        self._request_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._stream_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

        self._request_window_script = """
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

redis.call("ZREMRANGEBYSCORE", key, 0, now_ms - window_ms)
local count = redis.call("ZCARD", key)
if count >= limit then
    local oldest = redis.call("ZRANGE", key, 0, 0, "WITHSCORES")
    local retry_after = 1
    if oldest[2] then
        retry_after = math.ceil(((tonumber(oldest[2]) + window_ms) - now_ms) / 1000)
    end
    if retry_after < 1 then
        retry_after = 1
    end
    return {0, count, retry_after}
end

redis.call("ZADD", key, now_ms, member)
redis.call("PEXPIRE", key, window_ms + 1000)
return {1, count + 1, 0}
"""

        self._stream_acquire_script = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local ttl_ms = tonumber(ARGV[2])

local count = tonumber(redis.call("GET", key) or "0")
if count >= limit then
    return {0, count}
end

count = redis.call("INCR", key)
redis.call("PEXPIRE", key, ttl_ms)
if count > limit then
    redis.call("DECR", key)
    return {0, limit}
end

return {1, count}
"""

        self._stream_release_script = """
local key = KEYS[1]
local count = tonumber(redis.call("GET", key) or "0")
if count <= 0 then
    redis.call("DEL", key)
    return {0, 0}
end

count = redis.call("DECR", key)
if count <= 0 then
    redis.call("DEL", key)
    return {1, 0}
end

return {1, count}
"""

    @property
    def use_memory(self) -> bool:
        return self._use_memory

    async def allow_request(self, ip: str, route_key: str) -> RateLimitDecision:
        policy = self._policy(route_key)
        if policy.request_limit <= 0:
            return RateLimitDecision(False, policy.window_seconds, policy.request_limit, 0)

        if self._redis is not None:
            return await self._allow_request_redis(ip, route_key, policy)

        return await self._allow_request_memory(ip, route_key, policy)

    async def acquire_stream(self, ip: str, route_key: str) -> RateLimitDecision:
        policy = self._policy(route_key)
        if not policy.concurrent_stream_limit:
            return RateLimitDecision(True, 0, policy.request_limit, policy.request_limit)

        if self._redis is not None:
            return await self._acquire_stream_redis(ip, route_key, policy)

        return await self._acquire_stream_memory(ip, route_key, policy)

    async def release_stream(self, ip: str, route_key: str) -> None:
        policy = self._policy(route_key)
        if not policy.concurrent_stream_limit:
            return

        if self._redis is not None:
            await self._release_stream_redis(ip, route_key, policy)
            return

        await self._release_stream_memory(ip, route_key, policy)

    def _policy(self, route_key: str) -> RouteLimit:
        return self.policies.get(route_key, RouteLimit(request_limit=0, window_seconds=60))

    def _request_key(self, ip: str, route_key: str) -> str:
        return f"ratelimit:req:{route_key}:{ip}"

    def _stream_key(self, ip: str, route_key: str) -> str:
        return f"ratelimit:stream:{route_key}:{ip}"

    async def _allow_request_memory(
        self,
        ip: str,
        route_key: str,
        policy: RouteLimit,
    ) -> RateLimitDecision:
        key = self._request_key(ip, route_key)
        async with self._request_locks[key]:
            now = time.time()
            window_start = now - policy.window_seconds
            events = self._request_events[key]
            while events and events[0] <= window_start:
                events.popleft()

            if len(events) >= policy.request_limit:
                retry_after = max(1, math.ceil((events[0] + policy.window_seconds) - now))
                return RateLimitDecision(False, retry_after, policy.request_limit, 0)

            events.append(now)
            remaining = max(0, policy.request_limit - len(events))
            return RateLimitDecision(True, 0, policy.request_limit, remaining)

    async def _acquire_stream_memory(
        self,
        ip: str,
        route_key: str,
        policy: RouteLimit,
    ) -> RateLimitDecision:
        key = self._stream_key(ip, route_key)
        async with self._stream_locks[key]:
            active = self._active_stream_counts[key]
            if active >= policy.concurrent_stream_limit:
                return RateLimitDecision(False, policy.concurrent_retry_after_seconds, policy.concurrent_stream_limit, 0)

            self._active_stream_counts[key] = active + 1
            remaining = max(0, policy.concurrent_stream_limit - self._active_stream_counts[key])
            return RateLimitDecision(True, 0, policy.concurrent_stream_limit, remaining)

    async def _release_stream_memory(
        self,
        ip: str,
        route_key: str,
        policy: RouteLimit,
    ) -> None:
        key = self._stream_key(ip, route_key)
        async with self._stream_locks[key]:
            active = self._active_stream_counts[key]
            if active <= 1:
                self._active_stream_counts.pop(key, None)
            else:
                self._active_stream_counts[key] = active - 1

    async def _allow_request_redis(
        self,
        ip: str,
        route_key: str,
        policy: RouteLimit,
    ) -> RateLimitDecision:
        key = self._request_key(ip, route_key)
        now_ms = int(time.time() * 1000)
        window_ms = int(policy.window_seconds * 1000)
        member = uuid.uuid4().hex
        result = await self._redis.eval(
            self._request_window_script,
            1,
            key,
            now_ms,
            window_ms,
            policy.request_limit,
            member,
        )

        allowed = bool(int(result[0]))
        count = int(result[1])
        retry_after = int(result[2]) if len(result) > 2 else 0
        remaining = max(0, policy.request_limit - count) if allowed else 0
        return RateLimitDecision(allowed, retry_after, policy.request_limit, remaining)

    async def _acquire_stream_redis(
        self,
        ip: str,
        route_key: str,
        policy: RouteLimit,
    ) -> RateLimitDecision:
        key = self._stream_key(ip, route_key)
        ttl_ms = int(policy.active_ttl_seconds * 1000)
        result = await self._redis.eval(
            self._stream_acquire_script,
            1,
            key,
            policy.concurrent_stream_limit,
            ttl_ms,
        )
        allowed = bool(int(result[0]))
        count = int(result[1])
        remaining = max(0, policy.concurrent_stream_limit - count) if allowed else 0
        retry_after = 0 if allowed else policy.concurrent_retry_after_seconds
        return RateLimitDecision(allowed, retry_after, policy.concurrent_stream_limit, remaining)

    async def _release_stream_redis(
        self,
        ip: str,
        route_key: str,
        policy: RouteLimit,
    ) -> None:
        key = self._stream_key(ip, route_key)
        await self._redis.eval(self._stream_release_script, 1, key)

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
