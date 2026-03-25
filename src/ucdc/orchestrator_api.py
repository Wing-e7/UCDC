from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import write_audit_event
from .config import get_settings, validate_settings_for_startup
from .consent_hash import compute_consent_hash
from .db import get_db, init_db
from .jwt_utils import decode_consent_token
from .logging_middleware import RequestLoggingMiddleware
from .models import AuditEvent, Consent, Job
from .schemas import AuditEventOut, JobCancelResponse, JobDetail, JobRequest, JobResponse

logger = logging.getLogger("ucdc")


def _setup_logging() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)


_setup_logging()

@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_settings_for_startup()
    init_db()
    yield


app = FastAPI(title="UCDC Job Orchestrator", version="0.1", lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(select(1))
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB not ready: {e}") from e


@app.post("/jobs", response_model=JobResponse)
def schedule_job(req: JobRequest, db: Session = Depends(get_db)):
    payload = decode_consent_token(req.consent_token)

    consent_id = payload["consent_id"]
    user_id = payload["sub"]
    token_agent_id = payload["agent_id"]
    token_consent_hash = payload["consent_hash"]

    manifest = req.job_manifest

    if manifest.agent_id != token_agent_id:
        raise HTTPException(status_code=403, detail="Agent ID mismatch with consent")

    job_hash = compute_consent_hash(user_id=user_id, agent_id=manifest.agent_id, resources=manifest.resources)
    if job_hash != token_consent_hash:
        raise HTTPException(status_code=403, detail="Resources/manifest mismatch with consent")

    consent: Consent | None = db.get(Consent, consent_id)
    if not consent:
        raise HTTPException(status_code=403, detail="Consent not found for token")

    now = datetime.now(timezone.utc)
    if consent.revoked_at is not None:
        raise HTTPException(status_code=403, detail="Consent revoked")
    expires_at = consent.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise HTTPException(status_code=403, detail="Consent expired")

    job = Job(
        consent_id=consent.id,
        agent_id=manifest.agent_id,
        payload=manifest.model_dump(),
        status="scheduled",
        last_error=None,
        updated_at=now,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    write_audit_event(
        db,
        event_type="job.scheduled",
        consent_id=consent.id,
        job_id=job.id,
        details={"agent_id": manifest.agent_id},
    )

    logger.info("job_scheduled", extra={"job_id": job.id, "consent_id": consent_id})
    return JobResponse(job_id=job.id, status=job.status)


@app.get("/jobs/{job_id}", response_model=JobDetail)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobDetail(
        job_id=job.id,
        consent_id=job.consent_id,
        agent_id=job.agent_id,
        status=job.status,
        payload=dict(job.payload or {}),
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        cancelled_at=job.cancelled_at,
        last_error=job.last_error,
    )


@app.post("/jobs/{job_id}/cancel", response_model=JobCancelResponse)
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=409, detail=f"Job cannot be cancelled from status {job.status}")
    now = datetime.now(timezone.utc)
    job.status = "cancelled"
    job.cancelled_at = now
    job.updated_at = now
    db.add(job)
    db.commit()
    db.refresh(job)
    write_audit_event(
        db,
        event_type="job.cancelled",
        consent_id=job.consent_id,
        job_id=job.id,
        details={},
    )
    return JobCancelResponse(job_id=job.id, status=job.status, cancelled_at=job.cancelled_at)


@app.get("/jobs/{job_id}/events", response_model=list[AuditEventOut])
def list_job_events(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    rows = db.scalars(
        select(AuditEvent).where(AuditEvent.job_id == job_id).order_by(AuditEvent.created_at)
    ).all()
    return [
        AuditEventOut(
            id=r.id,
            consent_id=r.consent_id,
            job_id=r.job_id,
            event_type=r.event_type,
            details=dict(r.details or {}),
            created_at=r.created_at,
        )
        for r in rows
    ]

