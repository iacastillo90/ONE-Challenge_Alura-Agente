from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.dependencies import get_provider_router
from app.llm.router import ProviderRouter

router = APIRouter()


class SwitchProviderRequest(BaseModel):
    provider: str | None


@router.get("")
async def list_providers(
    router: ProviderRouter = Depends(get_provider_router),
):
    providers = await router.list_providers()
    return {
        "providers": providers,
        "active": router.get_active(),
    }


@router.post("/switch")
async def switch_provider(
    request: SwitchProviderRequest,
    router: ProviderRouter = Depends(get_provider_router),
):
    router.set_active(request.provider)
    return {"active": router.get_active()}
