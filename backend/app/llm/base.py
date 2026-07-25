from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator


@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class ProviderHealth:
    available: bool
    rate_limited: bool
    error: str | None = None


@dataclass
class TokenEvent:
    token: str
    done: bool = False
    full_response: str | None = None
    sources: list[dict] | None = None


class BaseProvider(ABC):
    name: str = ""
    model: str = ""
    priority: int = 99

    @abstractmethod
    async def check_health(self) -> ProviderHealth:
        ...

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[Message],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncGenerator[TokenEvent, None]:
        ...
        yield  # pragma: no cover
