from typing import AsyncGenerator

from loguru import logger
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.exceptions import ProviderRateLimitError, ProviderUnavailableError
from app.llm.base import BaseProvider, Message, ProviderHealth, TokenEvent


class OpenAICompatibleProvider(BaseProvider):
    name = "openai-compatible"
    model = ""
    priority = 4

    def __init__(self):
        if not settings.openai_compatible_api_key or not settings.openai_compatible_base_url:
            logger.warning("OpenAI-compatible provider not fully configured")
            self._client = None
        else:
            self._client = AsyncOpenAI(
                api_key=settings.openai_compatible_api_key,
                base_url=settings.openai_compatible_base_url,
            )
            self.model = settings.openai_compatible_base_url.rstrip("/").split("/")[-1] or "gpt-4o-mini"

    async def check_health(self) -> ProviderHealth:
        if not self._client:
            return ProviderHealth(available=False, rate_limited=False, error="Not configured")
        try:
            await self._client.models.list()
            return ProviderHealth(available=True, rate_limited=False)
        except Exception as e:
            return ProviderHealth(available=False, rate_limited=False, error=str(e))

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

        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "429" in error_str:
                raise ProviderRateLimitError(f"OpenAI-compatible rate limited: {e}")
            raise ProviderUnavailableError(f"OpenAI-compatible error: {e}")
