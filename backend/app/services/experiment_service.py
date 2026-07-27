from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.models import ExperimentRecord, FeedbackRecord
from app.core.retrieval_config import DEFAULT_CONFIG, RetrievalConfig




def _user_bucket(user_id: str) -> int:
    digest = hashlib.sha256(user_id.encode()).hexdigest()
    return int(digest[:8], 16) % 100


async def _load_active_experiments(session: AsyncSession) -> list[ExperimentRecord]:
    result = await session.execute(
        select(ExperimentRecord).where(ExperimentRecord.is_active)
    )
    return list(result.scalars().all())


async def resolve_config(user_id: str) -> tuple[RetrievalConfig, str | None]:
    bucket = _user_bucket(user_id)
    async with async_session_factory() as session:
        experiments = await _load_active_experiments(session)

    if not experiments:
        logger.debug(f"User {user_id[:8]}... → default config (no experiments)")
        return DEFAULT_CONFIG, None

    total_traffic = sum(e.traffic_percent for e in experiments)
    if total_traffic <= 0:
        logger.debug(f"User {user_id[:8]}... → default config (experiments have 0% traffic)")
        return DEFAULT_CONFIG, None

    cumulative = 0
    for exp in experiments:
        weight = max(0, exp.traffic_percent)
        cumulative += weight
        if bucket < cumulative:
            cfg = RetrievalConfig.from_dict(exp.config)
            cfg.name = exp.name
            logger.debug(
                f"User {user_id[:8]}... bucket={bucket} (cumulative={cumulative}/{total_traffic}) → experiment {exp.name} "
                f"(traffic={exp.traffic_percent}%)"
            )
            return cfg, exp.id

    logger.debug(f"User {user_id[:8]}... bucket={bucket} (cumulative={cumulative}/{total_traffic}) → default config")
    return DEFAULT_CONFIG, None


async def get_config(user_id: str) -> RetrievalConfig:
    cfg, _ = await resolve_config(user_id)
    return cfg


async def get_experiment_id(user_id: str) -> str | None:
    _, exp_id = await resolve_config(user_id)
    return exp_id


async def list_experiments(session: AsyncSession) -> list[ExperimentRecord]:
    result = await session.execute(
        select(ExperimentRecord).order_by(ExperimentRecord.created_at.desc())
    )
    return list(result.scalars().all())


async def get_experiment(session: AsyncSession, experiment_id: str) -> ExperimentRecord | None:
    return await session.get(ExperimentRecord, experiment_id)


async def create_experiment(
    session: AsyncSession,
    name: str,
    config: dict,
    description: str | None = None,
    traffic_percent: int = 10,
) -> ExperimentRecord:
    import uuid
    record = ExperimentRecord(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        config=config,
        is_active=True,
        traffic_percent=max(0, min(100, traffic_percent)),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    logger.info(f"Created experiment {record.name} (id={record.id[:8]}... traffic={record.traffic_percent}%)")
    return record


async def update_experiment(
    session: AsyncSession,
    experiment_id: str,
    **kwargs,
) -> ExperimentRecord | None:
    record = await session.get(ExperimentRecord, experiment_id)
    if record is None:
        return None
    for key, value in kwargs.items():
        if hasattr(record, key) and value is not None:
            setattr(record, key, value)
    record.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(record)
    return record


async def delete_experiment(session: AsyncSession, experiment_id: str) -> bool:
    record = await session.get(ExperimentRecord, experiment_id)
    if record is None:
        return False
    await session.delete(record)
    await session.commit()
    return True


async def get_experiment_stats(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        select(
            FeedbackRecord.experiment_id,
            func.count(FeedbackRecord.id).label("count"),
            func.avg(FeedbackRecord.rating).label("avg_rating"),
            func.min(FeedbackRecord.rating).label("min_rating"),
            func.max(FeedbackRecord.rating).label("max_rating"),
        )
        .where(FeedbackRecord.experiment_id.isnot(None))
        .group_by(FeedbackRecord.experiment_id)
    )
    rows = result.all()

    stats = []
    for row in rows:
        exp = None
        if row.experiment_id:
            exp = await session.get(ExperimentRecord, row.experiment_id)
        stats.append({
            "experiment_id": row.experiment_id,
            "experiment_name": exp.name if exp else "unknown",
            "feedback_count": row.count,
            "avg_rating": round(float(row.avg_rating), 2) if row.avg_rating else None,
            "min_rating": row.min_rating,
            "max_rating": row.max_rating,
        })

    control_result = await session.execute(
        select(
            func.count(FeedbackRecord.id).label("count"),
            func.avg(FeedbackRecord.rating).label("avg_rating"),
        )
        .where(FeedbackRecord.experiment_id.is_(None))
    )
    ctrl = control_result.one()
    stats.append({
        "experiment_id": None,
        "experiment_name": "control (default)",
        "feedback_count": ctrl.count,
        "avg_rating": round(float(ctrl.avg_rating), 2) if ctrl.avg_rating else None,
        "min_rating": None,
        "max_rating": None,
    })

    return stats
