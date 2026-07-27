from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_jwt
from app.core.database import get_db
from app.core.models import ExperimentRecord
from app.core.retrieval_config import BUILTIN_EXPERIMENTS
from app.services.experiment_service import (
    create_experiment,
    delete_experiment,
    get_experiment_stats,
    list_experiments,
    update_experiment,
)

router = APIRouter()


class ExperimentResponse(BaseModel):
    id: str
    name: str
    description: str | None
    config: dict
    is_active: bool
    traffic_percent: int
    created_at: datetime
    updated_at: datetime


class ExperimentCreate(BaseModel):
    name: str
    config: dict
    description: str | None = None
    traffic_percent: int = Field(default=10, ge=0, le=100)


class ExperimentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config: dict | None = None
    is_active: bool | None = None
    traffic_percent: int | None = Field(default=None, ge=0, le=100)


class BuiltinExperimentResponse(BaseModel):
    name: str
    config: dict


class StatsResponse(BaseModel):
    experiment_id: str | None
    experiment_name: str
    feedback_count: int
    avg_rating: float | None
    min_rating: int | None
    max_rating: int | None


@router.get("", response_model=list[ExperimentResponse])
async def list_experiments_endpoint(
    session: AsyncSession = Depends(get_db),
    _user_id: str = Depends(verify_jwt),
):
    records = await list_experiments(session)
    return [
        ExperimentResponse(
            id=r.id,
            name=r.name,
            description=r.description,
            config=r.config,
            is_active=r.is_active,
            traffic_percent=r.traffic_percent,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in records
    ]


@router.post("", response_model=ExperimentResponse, status_code=201)
async def create_experiment_endpoint(
    body: ExperimentCreate,
    session: AsyncSession = Depends(get_db),
    _user_id: str = Depends(verify_jwt),
):
    record = await create_experiment(
        session,
        name=body.name,
        config=body.config,
        description=body.description,
        traffic_percent=body.traffic_percent,
    )
    return ExperimentResponse(
        id=record.id,
        name=record.name,
        description=record.description,
        config=record.config,
        is_active=record.is_active,
        traffic_percent=record.traffic_percent,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("/builtins", response_model=list[BuiltinExperimentResponse])
async def list_builtins(
    _user_id: str = Depends(verify_jwt),
):
    return [
        BuiltinExperimentResponse(name=cfg.name, config=cfg.to_dict())
        for cfg in BUILTIN_EXPERIMENTS
    ]


@router.get("/stats", response_model=list[StatsResponse])
async def get_stats(
    session: AsyncSession = Depends(get_db),
    _user_id: str = Depends(verify_jwt),
):
    return await get_experiment_stats(session)


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment_endpoint(
    experiment_id: str,
    session: AsyncSession = Depends(get_db),
    _user_id: str = Depends(verify_jwt),
):
    record = await session.get(ExperimentRecord, experiment_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return ExperimentResponse(
        id=record.id,
        name=record.name,
        description=record.description,
        config=record.config,
        is_active=record.is_active,
        traffic_percent=record.traffic_percent,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.put("/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment_endpoint(
    experiment_id: str,
    body: ExperimentUpdate,
    session: AsyncSession = Depends(get_db),
    _user_id: str = Depends(verify_jwt),
):
    kwargs = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    record = await update_experiment(session, experiment_id, **kwargs)
    if record is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return ExperimentResponse(
        id=record.id,
        name=record.name,
        description=record.description,
        config=record.config,
        is_active=record.is_active,
        traffic_percent=record.traffic_percent,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.delete("/{experiment_id}", status_code=204)
async def delete_experiment_endpoint(
    experiment_id: str,
    session: AsyncSession = Depends(get_db),
    _user_id: str = Depends(verify_jwt),
):
    ok = await delete_experiment(session, experiment_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Experiment not found")
