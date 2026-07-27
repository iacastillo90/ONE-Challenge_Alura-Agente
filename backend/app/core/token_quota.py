import time

from loguru import logger
from prometheus_client import Counter

from app.core.cache import rag_cache
from app.core.exceptions import RAGException

TOKEN_CONSUMPTION = Counter(
    "token_consumption_total",
    "Total tokens consumed (input + output)",
    ["user_id_prefix"],
)

TOKEN_QUOTA_EXCEEDED = Counter(
    "token_quota_exceeded_total",
    "Total quota exceeded events",
    ["user_id_prefix"],
)

DAILY_TOKEN_BUDGET = 1_000_000
MINUTE_TOKEN_BUDGET = 50_000
WARNING_THRESHOLD = 0.8


class TokenQuotaTracker:
    def __init__(self, daily_budget: int = DAILY_TOKEN_BUDGET, minute_budget: int = MINUTE_TOKEN_BUDGET):
        self._daily_budget = daily_budget
        self._minute_budget = minute_budget

    def _daily_key(self, user_id: str) -> str:
        today = time.strftime("%Y-%m-%d")
        return f"token_quota:{user_id}:{today}"

    def _minute_key(self, user_id: str) -> str:
        minute = time.strftime("%Y%m%d%H%M")
        return f"token_rate:{user_id}:{minute}"

    async def check_only(self, user_id: str, input_tokens: int, estimated_output: int = 2048) -> None:
        total = input_tokens + estimated_output
        if total <= 0:
            return

        minute_key = self._minute_key(user_id)
        minute_used = await rag_cache.get(minute_key) or 0
        if isinstance(minute_used, int | float) and minute_used + total >= self._minute_budget:
            raise RAGException("Token rate limit approaching. Slow down your requests.")

        daily_key = self._daily_key(user_id)
        daily_used = await rag_cache.get(daily_key) or 0
        if isinstance(daily_used, int | float) and daily_used + total >= self._daily_budget:
            raise RAGException("Daily token budget exhausted. Try again tomorrow.")

    async def check_and_consume(self, user_id: str, input_tokens: int, output_tokens: int) -> None:
        total = input_tokens + output_tokens
        if total <= 0:
            return

        minute_key = self._minute_key(user_id)
        raw_minute = await rag_cache.incr(minute_key, total, ttl=70)
        if raw_minute >= self._minute_budget:
            logger.warning(f"Minute token budget exhausted for user {user_id[:8]}: {raw_minute}/{self._minute_budget}")
            TOKEN_QUOTA_EXCEEDED.labels(user_id_prefix=user_id[:8]).inc()
            raise RAGException("Token rate limit exceeded. Slow down your requests.")

        daily_key = self._daily_key(user_id)
        raw_daily = await rag_cache.incr(daily_key, total, ttl=86400)
        if raw_daily >= self._daily_budget:
            logger.warning(f"Daily token budget exhausted for user {user_id[:8]}: {raw_daily}/{self._daily_budget}")
            TOKEN_QUOTA_EXCEEDED.labels(user_id_prefix=user_id[:8]).inc()
            raise RAGException("Daily token budget exhausted. Try again tomorrow.")

        TOKEN_CONSUMPTION.labels(user_id_prefix=user_id[:8]).inc(total)

        ratio = raw_daily / self._daily_budget
        if ratio >= WARNING_THRESHOLD:
            logger.info(f"Token budget at {ratio:.0%} for user {user_id[:8]}: {raw_daily}/{self._daily_budget}")

    async def get_usage(self, user_id: str) -> dict:
        daily_key = self._daily_key(user_id)
        minute_key = self._minute_key(user_id)
        daily_used = await rag_cache.get(daily_key) or 0
        minute_used = await rag_cache.get(minute_key) or 0
        return {
            "used": daily_used,
            "budget": self._daily_budget,
            "remaining": max(0, self._daily_budget - daily_used),
            "pct": round(daily_used / self._daily_budget * 100, 1) if self._daily_budget else 0,
            "minute_used": minute_used,
            "minute_budget": self._minute_budget,
        }


token_quota = TokenQuotaTracker()
