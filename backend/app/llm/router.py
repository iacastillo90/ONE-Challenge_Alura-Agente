import asyncio
import time
from dataclasses import dataclass, field
from typing import AsyncGenerator

from loguru import logger

from app.core.exceptions import ProviderUnavailableError
from app.llm.base import BaseProvider, Message, ProviderHealth, TokenEvent


@dataclass
class ProviderState:
    provider: BaseProvider
    degraded_until: float = 0.0
    consecutive_failures: int = 0


class ProviderRouter:
    MAX_CONSECUTIVE_FAILURES = 3
    DEGRADED_TIMEOUT = 60.0

    def __init__(self, providers: list[BaseProvider]):
        self._states = [ProviderState(provider=p) for p in sorted(providers, key=lambda p: p.priority)]
        self._active_provider: str | None = None

    def set_active(self, provider_name: str | None):
        self._active_provider = provider_name

    def get_active(self) -> str | None:
        return self._active_provider

    async def list_providers(self) -> list[dict]:
        result = []
        for state in self._states:
            health = await state.provider.check_health()
            result.append({
                "name": state.provider.name,
                "model": state.provider.model,
                "priority": state.provider.priority,
                "available": health.available,
                "rate_limited": health.rate_limited,
                "degraded": time.time() < state.degraded_until,
            })
        return result

    def _get_candidates(self) -> list[ProviderState]:
        now = time.time()
        candidates = []

        if self._active_provider:
            for state in self._states:
                if state.provider.name == self._active_provider:
                    candidates.append(state)
                    break

        for state in self._states:
            if time.time() < state.degraded_until:
                logger.debug(f"Skipping degraded provider: {state.provider.name}")
                continue
            if state.provider.name != self._active_provider:
                candidates.append(state)

        return candidates

    async def generate_stream(
        self,
        messages: list[Message],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncGenerator[TokenEvent, None]:
        candidates = self._get_candidates()

        if not candidates:
            raise ProviderUnavailableError("No available LLM providers")

        last_error: Exception | None = None
        provider_names_attempted: list[str] = []

        for state in candidates:
            provider_names_attempted.append(state.provider.name)
            logger.info(f"Attempting provider: {state.provider.name}")

            try:
                health = await state.provider.check_health()
                if not health.available:
                    logger.warning(f"Provider {state.provider.name} unhealthy: {health.error}")
                    continue

                state.consecutive_failures = 0
                async for event in state.provider.generate_stream(
                    messages=messages, max_tokens=max_tokens, temperature=temperature
                ):
                    yield event

                return

            except Exception as e:
                last_error = e
                state.consecutive_failures += 1
                logger.error(f"Provider {state.provider.name} failed: {e}")

                if state.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                    state.degraded_until = time.time() + self.DEGRADED_TIMEOUT
                    logger.warning(f"Provider {state.provider.name} degraded for {self.DEGRADED_TIMEOUT}s")

                await asyncio.sleep(0.5)
                continue

        raise ProviderUnavailableError(
            f"All providers failed. Attempted: {', '.join(provider_names_attempted)}. Last error: {last_error}"
        )
