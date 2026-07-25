import pytest

from app.llm.base import BaseProvider, Message, ProviderHealth, TokenEvent
from app.llm.router import ProviderRouter


class MockProvider(BaseProvider):
    def __init__(self, name: str, priority: int, available: bool = True):
        self.name = name
        self.model = f"model-{name}"
        self.priority = priority
        self._available = available
        self._fail_count = 0
        self._fail_after = -1

    def fail_after(self, n: int):
        self._fail_after = n
        return self

    async def check_health(self) -> ProviderHealth:
        return ProviderHealth(available=self._available, rate_limited=False)

    async def generate_stream(self, messages, max_tokens=4096, temperature=0.7):
        if self._fail_after == -1 or self._fail_count < self._fail_after:
            self._fail_count += 1
            yield TokenEvent(token=f"from-{self.name}", done=True, full_response=f"from-{self.name}")
        else:
            raise Exception(f"{self.name} simulated failure")


@pytest.mark.asyncio
async def test_router_uses_highest_priority():
    p1 = MockProvider("p1", priority=1)
    p2 = MockProvider("p2", priority=2)
    router = ProviderRouter([p2, p1])

    tokens = []
    async for t in router.generate_stream([Message(role="user", content="test")]):
        tokens.append(t)

    assert any("from-p1" in str(t) for t in tokens)


@pytest.mark.asyncio
async def test_router_fallback_on_failure():
    p1 = MockProvider("p1", priority=1).fail_after(0)
    p2 = MockProvider("p2", priority=2)
    router = ProviderRouter([p1, p2])

    tokens = []
    async for t in router.generate_stream([Message(role="user", content="test")]):
        tokens.append(t)

    assert any("from-p2" in str(t) for t in tokens)


@pytest.mark.asyncio
async def test_router_all_providers_fail():
    p1 = MockProvider("p1", priority=1).fail_after(0)
    p2 = MockProvider("p2", priority=2).fail_after(0)
    router = ProviderRouter([p1, p2])

    with pytest.raises(Exception, match="All providers failed"):
        async for _ in router.generate_stream([Message(role="user", content="test")]):
            pass


@pytest.mark.asyncio
async def test_router_active_provider():
    p1 = MockProvider("p1", priority=1)
    p2 = MockProvider("p2", priority=2)
    router = ProviderRouter([p1, p2])
    router.set_active("p2")

    tokens = []
    async for t in router.generate_stream([Message(role="user", content="test")]):
        tokens.append(t)

    assert any("from-p2" in str(t) for t in tokens)


@pytest.mark.asyncio
async def test_router_list_providers():
    p1 = MockProvider("p1", priority=1)
    p2 = MockProvider("p2", priority=2, available=False)
    router = ProviderRouter([p1, p2])

    providers = await router.list_providers()
    assert len(providers) == 2
    assert providers[0]["name"] == "p1"
    assert providers[0]["available"] is True
    assert providers[1]["available"] is False
