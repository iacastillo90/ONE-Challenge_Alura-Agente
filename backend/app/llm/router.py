import asyncio
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from loguru import logger

from app.core.config import settings
from app.core.exceptions import ProviderUnavailableError
from app.core.otel import end_span, start_span
from app.llm.base import BaseProvider, Message, TokenEvent


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

    @property
    def provider_states(self) -> list[ProviderState]:
        return list(self._states)

    def set_active(self, provider_name: str | None):
        self._active_provider = provider_name

    def get_active(self) -> str | None:
        return self._active_provider

    def get_active_state(self) -> BaseProvider | None:
        if self._active_provider is None:
            return None
        for state in self._states:
            if state.provider.name == self._active_provider:
                return state.provider
        return None

    async def list_providers(self) -> list[dict]:
        result = []
        for state in self.provider_states:
            health = await state.provider.check_health()
            result.append({
                "name": state.provider.name,
                "model": state.provider.model,
                "priority": state.provider.priority,
                "available": health.available,
                "rate_limited": health.rate_limited,
                "degraded": time.time() < state.degraded_until,
                "error": "Unavailable" if not health.available else None,
            })
        return result

    def _get_candidates(self) -> list[ProviderState]:
        candidates = []

        if self._active_provider:
            for state in self._states:
                if state.provider.name == self._active_provider:
                    candidates.append(state)
                    break

        for state in self._states:
            if time.time() < state.degraded_until:
                logger.debug(f"Omitiendo proveedor degradado: {state.provider.name}")
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
            raise ProviderUnavailableError("No hay proveedores de LLM disponibles")

        provider_names_attempted: list[str] = []

        for state in candidates:
            provider_names_attempted.append(state.provider.name)
            logger.info(f"Intentando proveedor: {state.provider.name}")

            try:
                health = await state.provider.check_health()
                if not health.available:
                    logger.warning(f"El proveedor {state.provider.name} no está en estado óptimo (unhealthy)")
                    continue

                self._active_provider = state.provider.name

                span = start_span(f"llm.provider.{state.provider.name}", {
                    "provider": state.provider.name,
                    "model": state.provider.model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "message_count": len(messages),
                })
                try:
                    async with asyncio.timeout(settings.llm_timeout_seconds):
                        async for event in state.provider.generate_stream(
                            messages=messages,
                            max_tokens=max_tokens,
                            temperature=temperature,
                        ):
                            yield event
                except Exception as e:
                    end_span(span, e)
                    raise
                state.consecutive_failures = 0
                end_span(span)
                return

            except Exception as e:
                if not isinstance(e, asyncio.TimeoutError):
                    state.consecutive_failures += 1
                logger.error(f"El proveedor {state.provider.name} falló: {e}")

                if state.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                    state.degraded_until = time.time() + self.DEGRADED_TIMEOUT
                    logger.warning(f"El proveedor {state.provider.name} fue marcado como degradado por {self.DEGRADED_TIMEOUT}s")

                delay = min(settings.llm_retry_base_delay * (2 ** (len(provider_names_attempted) - 1)), 10.0)
                import random
                jitter = random.uniform(0, 0.5)
                await asyncio.sleep(delay + jitter)
                continue

        logger.error(f"Todos los proveedores fallaron. Se intentaron: {', '.join(provider_names_attempted)}.")
        raise ProviderUnavailableError(
            "Todos los proveedores fallaron — no hay proveedor LLM disponible. Por favor, reintente más tarde."
        )
