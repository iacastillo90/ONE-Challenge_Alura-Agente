import asyncio
import time

import redis.asyncio as aioredis
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings

IP_LIMIT = 600
IP_WINDOW = 60
USER_LIMIT = 300
USER_WINDOW = 60
GLOBAL_CONCURRENCY = 50


class RedisRateLimiter(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._redis: aioredis.Redis | None = None
        self._global_semaphore = asyncio.Semaphore(GLOBAL_CONCURRENCY)
        self._fallback = _InMemoryFallback()

    async def _get_redis(self) -> aioredis.Redis | None:
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    settings.redis_url,
                    socket_connect_timeout=1,
                    socket_timeout=1,
                )
                await self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _get_user_key(self, request: Request) -> str | None:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return f"jwt:{auth[7:16]}"
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return f"apikey:{api_key[:8]}"
        return None

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        client_ip = self._get_client_ip(request)
        user_key = self._get_user_key(request)

        r = await self._get_redis()
        if r is not None:
            ok, status = await self._check_redis(r, client_ip, user_key)
            if not ok:
                return status
        else:
            ok, status = self._fallback.check(client_ip, user_key)
            if not ok:
                return status

        try:
            async with asyncio.timeout(2.0):
                await self._global_semaphore.acquire()
        except TimeoutError:
            return JSONResponse(
                status_code=503,
                content={"error": {"code": "SERVER_BUSY", "message": "Server at capacity, try again later"}},
            )
        try:
            return await call_next(request)
        finally:
            self._global_semaphore.release()

    async def _check_redis(
        self, r: aioredis.Redis, client_ip: str, user_key: str | None
    ) -> tuple[bool, JSONResponse | None]:
        now_ts = int(time.time())
        ip_win = now_ts // IP_WINDOW
        ip_key = f"rl:ip:{client_ip}:{ip_win}"
        ip_count = await r.incr(ip_key)
        if ip_count == 1:
            await r.expire(ip_key, IP_WINDOW + 5)
        if ip_count > IP_LIMIT:
            return False, JSONResponse(
                status_code=429,
                content={"error": {"code": "RATE_LIMITED_IP", "message": "Too many requests from this IP"}},
                headers={"Retry-After": str(IP_WINDOW)},
            )

        if user_key:
            user_win = now_ts // USER_WINDOW
            u_key = f"rl:user:{user_key}:{user_win}"
            u_count = await r.incr(u_key)
            if u_count == 1:
                await r.expire(u_key, USER_WINDOW + 5)
            if u_count > USER_LIMIT:
                return False, JSONResponse(
                    status_code=429,
                    content={"error": {"code": "RATE_LIMITED_USER", "message": "Too many requests"}},
                    headers={"Retry-After": str(USER_WINDOW)},
                )

        return True, None


class _InMemoryFallback:
    """Per-process sliding-window fallback used when Redis is unreachable.

    Fails *open* for availability but still enforces limits within each worker
    process, so a Redis outage degrades (limits become per-process rather than
    global) instead of taking the whole API down with 503s.
    """

    def __init__(self):
        self._counters: dict[str, tuple[int, int]] = {}
        self._logged = False

    def _hit(self, key: str, window: int, limit: int) -> bool:
        now_win = int(time.time()) // window
        count, win = self._counters.get(key, (0, now_win))
        if win != now_win:
            count, win = 0, now_win
        count += 1
        self._counters[key] = (count, win)
        # Opportunistic cleanup to bound memory.
        if len(self._counters) > 10000:
            self._counters = {k: v for k, v in self._counters.items() if v[1] >= now_win}
        return count <= limit

    def check(self, client_ip: str, user_key: str | None) -> tuple[bool, JSONResponse | None]:
        if not self._logged:
            logger.warning("Rate limiter falling back to in-memory (Redis unavailable) — limits are now per-process")
            self._logged = True

        if not self._hit(f"ip:{client_ip}", IP_WINDOW, IP_LIMIT):
            return False, JSONResponse(
                status_code=429,
                headers={"Retry-After": str(IP_WINDOW)},
                content={"error": {"code": "RATE_LIMITED_IP", "message": "Too many requests from this IP"}},
            )
        if user_key and not self._hit(f"user:{user_key}", USER_WINDOW, USER_LIMIT):
            return False, JSONResponse(
                status_code=429,
                headers={"Retry-After": str(USER_WINDOW)},
                content={"error": {"code": "RATE_LIMITED_USER", "message": "Too many requests"}},
            )
        return True, None
