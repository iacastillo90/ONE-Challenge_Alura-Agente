from abc import ABC, abstractmethod
from dataclasses import dataclass
from collections.abc import AsyncGenerator


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
    experiment_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


class BaseProvider(ABC):
    name: str = ""
    model: str = ""
    priority: int = 99
    context_window: int = 8192

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
