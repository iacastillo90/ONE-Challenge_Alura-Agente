import asyncio
import json
import time
from collections import OrderedDict

from loguru import logger

from app.core.config import settings


class SimpleCache:
    def __init__(self, maxsize: int = 256, ttl: int = 300):
        self._maxsize = maxsize
        self._ttl = ttl
        self._store: OrderedDict[str, tuple[float, object]] = OrderedDict()

    def get(self, key: str) -> object | None:
        if key not in self._store:
            return None
        expires, value = self._store[key]
        if time.time() > expires:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key: str, value: object, ttl: int | None = None):
        expires = time.time() + (ttl or self._ttl)
        self._store[key] = (expires, value)
        self._store.move_to_end(key)
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)

    def invalidate(self, key: str):
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()

    def get_dict(self, key: str) -> dict | None:
        val = self.get(key)
        return val if isinstance(val, dict) else None

    def set_dict(self, key: str, value: dict, ttl: int | None = None):
        self.set(key, value, ttl=ttl)


class RedisCache:
    def __init__(self, default_ttl: int = 300):
        self._default_ttl = default_ttl
        self._redis = None
        self._fallback = SimpleCache(maxsize=128, ttl=default_ttl)

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(
                    settings.redis_url,
                    socket_connect_timeout=1,
                    socket_timeout=1,
                    decode_responses=False,
                )
                await self._redis.ping()
                logger.info("Redis cache connected")
            except Exception:
                logger.warning("Redis unavailable for cache, falling back to in-memory")
                self._redis = False
        return self._redis if self._redis is not False else None

    async def get(self, key: str) -> object | None:
        r = await self._get_redis()
        if r is not None:
            raw = await r.get(key)
            if raw is None:
                return None
            try:
                return json.loads(raw.decode("utf-8"))
            except Exception:
                return None
        return self._fallback.get(key)

    async def set(self, key: str, value: object, ttl: int | None = None):
        r = await self._get_redis()
        ttl_sec = ttl or self._default_ttl
        if r is not None:
            raw = json.dumps(value, default=str).encode("utf-8")
            await r.setex(key, ttl_sec, raw)
        else:
            self._fallback.set(key, value, ttl=ttl_sec)

    async def invalidate(self, key: str):
        r = await self._get_redis()
        if r is not None:
            await r.delete(key)
        self._fallback.invalidate(key)

    async def clear(self):
        r = await self._get_redis()
        if r is not None:
            await r.flushdb()
        self._fallback.clear()

    async def incr(self, key: str, amount: int = 1, ttl: int | None = None) -> int:
        r = await self._get_redis()
        if r is not None:
            new_val = await r.incr(key, amount)
            ttl_sec = ttl or self._default_ttl
            await r.expire(key, ttl_sec)
            return new_val
        val = self._fallback.get(key) or 0
        new_val = val + amount
        self._fallback.set(key, new_val, ttl=ttl)
        return new_val

    async def get_dict(self, key: str) -> dict | None:
        val = await self.get(key)
        return val if isinstance(val, dict) else None

    async def set_dict(self, key: str, value: dict, ttl: int | None = None):
        await self.set(key, value, ttl=ttl)


rag_cache = RedisCache(default_ttl=settings.cache_ttl_seconds)


class DistributedLock:
    def __init__(self, rag_cache_instance: RedisCache, prefix: str = "distlock", default_timeout: int = 30):
        self._cache = rag_cache_instance
        self._prefix = prefix
        self._default_timeout = default_timeout
        self._fallback: dict[str, asyncio.Lock] = {}

    def _key(self, name: str) -> str:
        return f"{self._prefix}:{name}"

    async def run_with_lock(self, name: str, timeout: int | None = None):
        ttl = timeout or self._default_timeout
        key = self._key(name)
        r = await self._cache._get_redis()
        if r is not None:
            for _attempt in range(50):
                acquired = await r.setnx(key, "1")
                if acquired:
                    await r.expire(key, ttl)
                    self._current_name = name
                    self._redis_conn = r
                    return self
                await asyncio.sleep(0.05)
            raise TimeoutError(f"Could not acquire distributed lock: {name}")
        lock = self._fallback.setdefault(name, asyncio.Lock())
        await lock.acquire()
        self._current_name = name
        self._redis_conn = None
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._redis_conn is not None:
            await self._redis_conn.delete(self._key(self._current_name))
        elif self._current_name in self._fallback:
            try:
                self._fallback[self._current_name].release()
            except RuntimeError:
                pass


dist_lock = DistributedLock(rag_cache)
