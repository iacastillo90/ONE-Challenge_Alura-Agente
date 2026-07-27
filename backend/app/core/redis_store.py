from __future__ import annotations

import time
from datetime import datetime, timezone

from loguru import logger

from app.core.cache import rag_cache


class RedisBackedSet:
    def __init__(self, prefix: str):
        self._prefix = prefix

    def _key(self, member: str) -> str:
        return f"{self._prefix}:{member}"

    async def add(self, member: str, ttl_seconds: int = 86400) -> None:
        await rag_cache.set(self._key(member), True, ttl=ttl_seconds)

    async def contains(self, member: str) -> bool:
        val = await rag_cache.get(self._key(member))
        return val is not None

    async def remove(self, member: str) -> None:
        await rag_cache.invalidate(self._key(member))


class RedisBackedDict:
    def __init__(self, prefix: str):
        self._prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    async def get(self, key: str) -> dict | None:
        val = await rag_cache.get(self._key(key))
        return val if isinstance(val, dict) else None

    async def set(self, key: str, value: dict, ttl_seconds: int = 86400 * 30) -> None:
        await rag_cache.set(self._key(key), value, ttl=ttl_seconds)

    async def delete(self, key: str) -> None:
        await rag_cache.invalidate(self._key(key))

    async def find_by_value(self, field: str, target: str) -> list[str]:
        return []


jwt_blacklist = RedisBackedSet("jwt_blacklist")
refresh_tokens = RedisBackedDict("refresh_token")


async def blacklist_jti(jti: str, expires_at: datetime | None = None):
    ttl = max(60, int((expires_at - datetime.now(timezone.utc)).total_seconds())) if expires_at else 86400
    await jwt_blacklist.add(jti, ttl_seconds=ttl)


async def is_jti_blacklisted(jti: str) -> bool:
    return await jwt_blacklist.contains(jti)


def _user_refresh_index_key(user_id: str) -> str:
    return f"user_refresh_index:{user_id}"


async def _index_add(user_id: str, token: str, ttl_seconds: int) -> None:
    """Track a user's active refresh tokens so we can revoke them all on logout.

    Uses a native Redis set when available; falls back to a JSON list in the
    in-memory cache when Redis is not reachable.
    """
    r = await rag_cache._get_redis()
    key = _user_refresh_index_key(user_id)
    if r is not None:
        await r.sadd(key, token)
        await r.expire(key, ttl_seconds)
        return
    tokens = await rag_cache.get(key) or []
    if token not in tokens:
        tokens.append(token)
    await rag_cache.set(key, tokens, ttl=ttl_seconds)


async def _index_remove(user_id: str, token: str) -> None:
    r = await rag_cache._get_redis()
    key = _user_refresh_index_key(user_id)
    if r is not None:
        await r.srem(key, token)
        return
    tokens = await rag_cache.get(key) or []
    if token in tokens:
        tokens.remove(token)
        await rag_cache.set(key, tokens)


async def store_refresh_token(token: str, user_id: str, expires_at: datetime):
    ttl = max(60, int((expires_at - datetime.now(timezone.utc)).total_seconds()))
    await refresh_tokens.set(token, {
        "user_id": user_id,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }, ttl_seconds=ttl)
    await _index_add(user_id, token, ttl)


async def get_refresh_token_data(token: str) -> dict | None:
    data = await refresh_tokens.get(token)
    if data is None:
        return None
    expires = datetime.fromisoformat(data["expires_at"])
    if datetime.now(timezone.utc) > expires:
        await refresh_tokens.delete(token)
        return None
    return data


async def revoke_refresh_token(token: str):
    data = await refresh_tokens.get(token)
    await refresh_tokens.delete(token)
    if isinstance(data, dict) and data.get("user_id"):
        await _index_remove(data["user_id"], token)


async def revoke_all_user_refresh_tokens(user_id: str):
    """Revoke every active refresh token for a user (real logout-everywhere)."""
    key = _user_refresh_index_key(user_id)
    r = await rag_cache._get_redis()
    if r is not None:
        tokens = await r.smembers(key)
        for raw in tokens:
            token = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            await refresh_tokens.delete(token)
        await r.delete(key)
        return
    tokens = await rag_cache.get(key) or []
    for token in tokens:
        await refresh_tokens.delete(token)
    await rag_cache.invalidate(key)


LOGIN_PREFIX = "login_attempts"


async def get_login_attempts(username: str) -> tuple[int, float]:
    key = f"{LOGIN_PREFIX}:{username}"
    data = await rag_cache.get(key)
    if data is None:
        return 0, 0.0
    return data.get("attempts", 0), data.get("lock_until", 0.0)


async def increment_login_attempts(username: str, max_attempts: int = 5, lockout_seconds: int = 300):
    key = f"{LOGIN_PREFIX}:{username}"
    data = await rag_cache.get(key) or {}
    attempts = data.get("attempts", 0) + 1
    lock_until = 0.0
    if attempts >= max_attempts:
        lock_until = time.time() + lockout_seconds
        logger.warning(f"Login locked for {username} after {max_attempts} failed attempts")
    await rag_cache.set(key, {"attempts": attempts, "lock_until": lock_until}, ttl=lockout_seconds + 60)
    return attempts, lock_until


async def reset_login_attempts(username: str):
    key = f"{LOGIN_PREFIX}:{username}"
    await rag_cache.invalidate(key)


REGISTER_PREFIX = "register_rate"


async def check_register_rate(ip: str, max_per_hour: int = 3) -> tuple[bool, int]:
    hour = time.strftime("%Y%m%d%H")
    key = f"{REGISTER_PREFIX}:{ip}:{hour}"
    count = await rag_cache.get(key) or 0
    if count >= max_per_hour:
        return False, max_per_hour - count
    return True, max_per_hour - count - 1


async def increment_register_count(ip: str):
    hour = time.strftime("%Y%m%d%H")
    key = f"{REGISTER_PREFIX}:{ip}:{hour}"
    count = await rag_cache.get(key) or 0
    await rag_cache.set(key, count + 1, ttl=3600)
