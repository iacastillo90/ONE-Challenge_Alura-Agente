import asyncio
from typing import AsyncGenerator

from loguru import logger
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.exceptions import ProviderRateLimitError, ProviderUnavailableError
from app.llm.base import BaseProvider, Message, ProviderHealth, TokenEvent


class DeepSeekProvider(BaseProvider):
    name = "deepseek"
    model = "deepseek-chat"
    priority = 3
    context_window = 64_000

    def __init__(self):
        if not settings.deepseek_api_key:
            logger.warning("DeepSeek API key not configured")
            self._client = None
        else:
            self._client = AsyncOpenAI(
                api_key=settings.deepseek_api_key,
                base_url="https://api.deepseek.com",
            )

    async def check_health(self) -> ProviderHealth:
        if not self._client:
            return ProviderHealth(available=False, rate_limited=False, error="API key not configured")
        try:
            async with asyncio.timeout(10):
                await self._client.models.retrieve(model=self.model)
            return ProviderHealth(available=True, rate_limited=False)
        except Exception as e:
            logger.warning(f"DeepSeek health check failed: {e}")
            return ProviderHealth(available=False, rate_limited=False, error=str(e))

    async def generate_stream(
        self,
        messages: list[Message],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncGenerator[TokenEvent, None]:
        if not self._client:
            raise ProviderUnavailableError("DeepSeek API key not configured")

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
            raise ProviderUnavailableError("DeepSeek: timeout exceeded")
        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "429" in error_str:
                raise ProviderRateLimitError("DeepSeek: rate limit exceeded")
            raise ProviderUnavailableError("DeepSeek: provider error")
