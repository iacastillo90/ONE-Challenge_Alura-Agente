from collections.abc import Callable, Coroutine
from dataclasses import dataclass

from loguru import logger

rate_limit_logger = logger


@dataclass
class HealthStatus:
    name: str
    ok: bool
    detail: str | None = None


class HealthRegistry:
    def __init__(self):
        self._checks: list[tuple[str, Callable[[], Coroutine]]] = []

    def register(self, name: str, check_fn: Callable[[], Coroutine]):
        self._checks.append((name, check_fn))

    async def check_all(self) -> list[HealthStatus]:
        import asyncio
        results = []
        for name, fn in self._checks:
            try:
                ok = await asyncio.wait_for(fn(), timeout=5.0)
                results.append(HealthStatus(name=name, ok=bool(ok)))
            except TimeoutError:
                results.append(HealthStatus(name=name, ok=False, detail="timeout"))
            except Exception as e:
                results.append(HealthStatus(name=name, ok=False, detail=str(e)))
        return results

    @property
    async def overall(self) -> str:
        results = await self.check_all()
        if all(r.ok for r in results):
            return "healthy"
        if any(r.ok for r in results):
            return "degraded"
        return "unhealthy"


health_registry = HealthRegistry()
