from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import AgentEntitlement, Consent, Job


def _max_concurrent_for(db: Session, user_id: str, agent_id: str) -> int:
    row = db.execute(
        select(AgentEntitlement.max_concurrent_jobs).where(
            AgentEntitlement.user_id == user_id,
            AgentEntitlement.agent_id == agent_id,
        )
    ).scalar_one_or_none()
    if row is not None:
        return int(row)
    return get_settings().default_max_concurrent_jobs


def count_active_jobs(
    db: Session,
    *,
    user_id: str,
    agent_id: str,
    exclude_job_id: str | None = None,
) -> int:
    stmt = (
        select(func.count())
        .select_from(Job)
        .join(Consent, Job.consent_id == Consent.id)
        .where(
            Consent.user_id == user_id,
            Job.agent_id == agent_id,
            Job.status.in_(("queued", "scheduled", "running")),
        )
    )
    if exclude_job_id:
        stmt = stmt.where(Job.id != exclude_job_id)
    return int(db.execute(stmt).scalar_one())


def enforce_enqueue_admission(db: Session, *, user_id: str, agent_id: str) -> None:
    limit = _max_concurrent_for(db, user_id, agent_id)
    current = count_active_jobs(db, user_id=user_id, agent_id=agent_id)
    if current >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Admission denied: max concurrent jobs ({limit}) reached for this user and agent",
        )


def enforce_dequeue_admission(
    db: Session,
    *,
    user_id: str,
    agent_id: str,
    job_id: str,
) -> None:
    limit = _max_concurrent_for(db, user_id, agent_id)
    current = count_active_jobs(db, user_id=user_id, agent_id=agent_id, exclude_job_id=job_id)
    if current >= limit:
        raise RuntimeError(
            f"Dequeue admission denied: would exceed max concurrent jobs ({limit}) for user/agent"
        )
