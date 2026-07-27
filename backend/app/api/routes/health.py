from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.dependencies import (
    get_provider_router,
    get_vector_store,
)
from app.llm.router import ProviderRouter
from app.rag.vector_store.base import VectorStore

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    vector_store: str
    llm_providers: dict


@router.get("/health", response_model=HealthResponse)
async def health_check(
    store: VectorStore = Depends(get_vector_store),
    router: ProviderRouter = Depends(get_provider_router),
):
    db_status = "ok"
    vs_status = "ok"
    try:
        stats = await store.get_collection_stats()
        _ = stats.count
    except Exception:
        vs_status = "error"

    try:
        from app.core.database import engine
        async with engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
    except Exception:
        db_status = "error"

    llm_status = {}
    for state in router.provider_states:
        try:
            health = await state.provider.check_health()
            llm_status[state.provider.name] = "available" if health.available else "unavailable"
        except Exception:
            llm_status[state.provider.name] = "error"

    overall = "ok" if db_status == "ok" and vs_status == "ok" else "degraded"
    return HealthResponse(
        status=overall,
        version="2.0.0",
        database=db_status,
        vector_store=vs_status,
        llm_providers=llm_status,
    )
