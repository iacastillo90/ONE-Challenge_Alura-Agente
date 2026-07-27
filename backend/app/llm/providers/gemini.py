import asyncio
from collections.abc import AsyncGenerator

from google import genai
from google.genai import types as gemini_types
from loguru import logger

from app.core.config import settings
from app.core.exceptions import ProviderRateLimitError, ProviderUnavailableError
from app.llm.base import BaseProvider, Message, ProviderHealth, TokenEvent


class GeminiProvider(BaseProvider):
    name = "google-gemini"
    model = "gemini-2.0-flash"
    priority = 1
    context_window = 1_048_576

    def __init__(self):
        if not settings.gemini_api_key:
            logger.warning("Gemini API key not configured")
            self._client = None
        else:
            self._client = genai.Client(api_key=settings.gemini_api_key)

    async def check_health(self) -> ProviderHealth:
        if not self._client:
            return ProviderHealth(available=False, rate_limited=False, error="API key not configured")
        try:
            async with asyncio.timeout(10):
                await self._client.aio.models.get(model=self.model)
            return ProviderHealth(available=True, rate_limited=False)
        except Exception:
            return ProviderHealth(available=False, rate_limited=False, error="Unavailable")

    async def generate_stream(
        self,
        messages: list[Message],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncGenerator[TokenEvent, None]:
        if not self._client:
            raise ProviderUnavailableError("Gemini API key not configured")

        gemini_messages = [
            gemini_types.Content(role=m.role, parts=[gemini_types.Part.from_text(text=m.content)])
            for m in messages
        ]

        try:
            response = await self._client.aio.models.generate_content_stream(
                model=self.model,
                contents=gemini_messages,
                config=gemini_types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                ),
            )

            full = ""
            async for chunk in response:
                if chunk.text:
                    full += chunk.text
                    yield TokenEvent(token=chunk.text)

            yield TokenEvent(token="", done=True, full_response=full)

        except TimeoutError:
            raise ProviderUnavailableError("Gemini: timeout exceeded")
        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "quota" in error_str or "429" in error_str:
                raise ProviderRateLimitError("Gemini: rate limit exceeded")
            raise ProviderUnavailableError("Gemini: provider error")
