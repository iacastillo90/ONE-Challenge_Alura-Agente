import asyncio
from collections.abc import AsyncGenerator
from urllib.parse import urlparse

from loguru import logger
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.exceptions import ProviderRateLimitError, ProviderUnavailableError
from app.llm.base import BaseProvider, Message, ProviderHealth, TokenEvent

SSRF_BLOCKED_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0", "metadata", "metadata.google.internal", "169.254.169.254")


class OpenAICompatibleProvider(BaseProvider):
    name = "openai-compatible"
    model = ""
    priority = 4
    context_window = 128_000

    def __init__(self):
        if not settings.openai_compatible_api_key or not settings.openai_compatible_base_url:
            logger.warning("OpenAI-compatible provider not fully configured")
            self._client = None
        else:
            parsed = urlparse(settings.openai_compatible_base_url)
            if parsed.hostname in SSRF_BLOCKED_HOSTS:
                raise RuntimeError(
                    f"SSRF blocked: OPENAI_COMPATIBLE_BASE_URL points to internal host ({parsed.hostname})"
                )
            self._client = AsyncOpenAI(
                api_key=settings.openai_compatible_api_key,
                base_url=settings.openai_compatible_base_url,
            )
            self.model = settings.openai_compatible_model or settings.openai_compatible_base_url.rstrip("/").split("/")[-1] or "gpt-4o-mini"

    async def check_health(self) -> ProviderHealth:
        if not self._client:
            return ProviderHealth(available=False, rate_limited=False, error="Not configured")
        try:
            async with asyncio.timeout(10):
                await self._client.models.retrieve(model=self.model)
            return ProviderHealth(available=True, rate_limited=False)
        except Exception:  # noqa: BLE001
            return ProviderHealth(available=False, rate_limited=False, error="Unavailable")

    async def generate_stream(
        self,
        messages: list[Message],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncGenerator[TokenEvent, None]:
        if not self._client:
            raise ProviderUnavailableError("OpenAI-compatible provider not configured")

        openai_messages = [{"role": m.role, "content": m.content} for m in messages]

        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            full = ""
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    full += delta.content
                    yield TokenEvent(token=delta.content)

            yield TokenEvent(token="", done=True, full_response=full)

        except asyncio.TimeoutError:
            raise ProviderUnavailableError("OpenAI-compatible: timeout exceeded")
        except Exception as e:  # noqa: BLE001
            error_str = str(e).lower()
            if "rate" in error_str or "429" in error_str:
                raise ProviderRateLimitError("OpenAI-compatible: rate limit exceeded")
            raise ProviderUnavailableError("OpenAI-compatible: provider error")
