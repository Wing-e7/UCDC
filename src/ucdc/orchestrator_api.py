from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import write_audit_event
from .config import get_settings, validate_settings_for_startup
from .consent_hash import consent_hash_from_job_manifest
from .cors_setup import add_cors
from .db import get_db, init_db
from .entitlements import enforce_enqueue_admission
from .job_execution import run_adapter_and_finalize
from .jwt_utils import decode_consent_token
from .logging_middleware import RequestLoggingMiddleware
from .models import (
    AuditEvent,
    Consent,
    Job,
    StafferApproval,
    StafferInstaller,
    StafferLaunchValidation,
)
from .schemas import (
    AuditEventOut,
    JobCancelResponse,
    JobDetail,
    JobManifest,
    JobRequest,
    JobResponse,
    StafferApprovalRequest,
    StafferInstallerCreateRequest,
    StafferInstallerOut,
    StafferLaunchValidationRequest,
)

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
add_cors(app)


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


@app.post(
    "/jobs",
    response_model=JobResponse,
    responses={200: {"model": JobResponse}, 202: {"model": JobResponse}},
)
def schedule_job(req: JobRequest, db: Session = Depends(get_db)):
    payload = decode_consent_token(req.consent_token)

    consent_id = payload["consent_id"]
    user_id = payload["sub"]
    token_agent_id = payload["agent_id"]
    token_consent_hash = payload["consent_hash"]

    manifest = req.job_manifest

    if manifest.agent_id != token_agent_id:
        raise HTTPException(status_code=403, detail="Agent ID mismatch with consent")

    job_hash = consent_hash_from_job_manifest(user_id=user_id, manifest=manifest)
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

    enforce_enqueue_admission(db, user_id=user_id, agent_id=manifest.agent_id)

    settings = get_settings()
    skip_adapter = os.getenv("UCDC_SKIP_ADAPTER_INTEGRATION") == "1"
    use_async = settings.ucdc_async_jobs and not skip_adapter
    initial_status = "queued" if use_async else "scheduled"

    job = Job(
        consent_id=consent.id,
        agent_id=manifest.agent_id,
        payload=manifest.model_dump(),
        status=initial_status,
        last_error=None,
        updated_at=now,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    event_type = "job.queued" if use_async else "job.scheduled"
    write_audit_event(
        db,
        event_type=event_type,
        consent_id=consent.id,
        job_id=job.id,
        details={"agent_id": manifest.agent_id, "async": use_async},
    )

    logger.info("job_created", extra={"job_id": job.id, "consent_id": consent_id, "async": use_async})

    if skip_adapter:
        return JobResponse(job_id=job.id, status=job.status)

    if use_async:
        return JSONResponse(status_code=202, content=JobResponse(job_id=job.id, status=job.status).model_dump())

    req_token = req.consent_token
    run_adapter_and_finalize(db, job, consent, manifest, consent_token=req_token)
    db.refresh(job)
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
            staffer_installer_id=r.staffer_installer_id,
            event_type=r.event_type,
            details=dict(r.details or {}),
            created_at=r.created_at,
        )
        for r in rows
    ]


STAFFER_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "submit": {"draft"},
    "approve": {"submitted"},
    "reject": {"submitted"},
    "validate-launch": {"approved"},
    "activate": {"launch_validated"},
    "rollback": {"approved", "launch_validation_failed", "launch_validated", "active"},
}


def _installer_out(installer: StafferInstaller) -> StafferInstallerOut:
    return StafferInstallerOut(
        id=installer.id,
        state=installer.state,
        payload=dict(installer.payload or {}),
        created_at=installer.created_at,
        updated_at=installer.updated_at,
        submitted_at=installer.submitted_at,
        approved_at=installer.approved_at,
        rejected_at=installer.rejected_at,
        launch_validated_at=installer.launch_validated_at,
        activated_at=installer.activated_at,
        rolled_back_at=installer.rolled_back_at,
    )


def _get_installer_or_404(db: Session, installer_id: str) -> StafferInstaller:
    installer = db.get(StafferInstaller, installer_id)
    if not installer:
        raise HTTPException(status_code=404, detail="Staffer installer not found")
    return installer


def _require_transition(installer: StafferInstaller, action: str) -> None:
    allowed_from = STAFFER_ALLOWED_TRANSITIONS[action]
    if installer.state not in allowed_from:
        raise HTTPException(
            status_code=409,
            detail=f"Installer cannot {action} from state {installer.state}",
        )


def _set_transition_fields(installer: StafferInstaller, *, action: str, now: datetime) -> None:
    installer.updated_at = now
    if action == "submit":
        installer.state = "submitted"
        installer.submitted_at = now
    elif action == "approve":
        installer.state = "approved"
        installer.approved_at = now
    elif action == "reject":
        installer.state = "rejected"
        installer.rejected_at = now
    elif action == "activate":
        installer.state = "active"
        installer.activated_at = now
    elif action == "rollback":
        installer.state = "rolled_back"
        installer.rolled_back_at = now


@app.post("/staffer/installers", response_model=StafferInstallerOut)
def create_staffer_installer(req: StafferInstallerCreateRequest, db: Session = Depends(get_db)):
    installer = StafferInstaller(payload=req.payload, state="draft")
    db.add(installer)
    db.commit()
    db.refresh(installer)
    write_audit_event(
        db,
        event_type="staffer.installer.created",
        staffer_installer_id=installer.id,
        details={"state": installer.state},
    )
    return _installer_out(installer)


@app.get("/staffer/installers/{installer_id}", response_model=StafferInstallerOut)
def get_staffer_installer(installer_id: str, db: Session = Depends(get_db)):
    installer = _get_installer_or_404(db, installer_id)
    return _installer_out(installer)


@app.get("/staffer/installers/{installer_id}/events", response_model=list[AuditEventOut])
def list_staffer_installer_events(installer_id: str, db: Session = Depends(get_db)):
    _get_installer_or_404(db, installer_id)
    rows = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.staffer_installer_id == installer_id)
        .order_by(AuditEvent.created_at)
    ).all()
    return [
        AuditEventOut(
            id=r.id,
            consent_id=r.consent_id,
            job_id=r.job_id,
            staffer_installer_id=r.staffer_installer_id,
            event_type=r.event_type,
            details=dict(r.details or {}),
            created_at=r.created_at,
        )
        for r in rows
    ]


@app.post("/staffer/installers/{installer_id}/submit", response_model=StafferInstallerOut)
def submit_staffer_installer(installer_id: str, db: Session = Depends(get_db)):
    installer = _get_installer_or_404(db, installer_id)
    _require_transition(installer, "submit")
    now = datetime.now(timezone.utc)
    _set_transition_fields(installer, action="submit", now=now)
    db.add(installer)
    db.commit()
    db.refresh(installer)
    write_audit_event(
        db,
        event_type="staffer.installer.submitted",
        staffer_installer_id=installer.id,
        details={"state": installer.state},
    )
    return _installer_out(installer)


def _handle_staffer_approval_action(
    *,
    installer: StafferInstaller,
    db: Session,
    action: str,
    idempotency_key: str | None,
    reason: str | None,
) -> StafferInstallerOut:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    existing = db.scalar(
        select(StafferApproval).where(
            StafferApproval.staffer_installer_id == installer.id,
            StafferApproval.idempotency_key == idempotency_key,
        )
    )
    if existing:
        if existing.action != action:
            raise HTTPException(
                status_code=409,
                detail=f"Idempotency key already used for action {existing.action}",
            )
        return _installer_out(installer)

    _require_transition(installer, action)
    now = datetime.now(timezone.utc)
    _set_transition_fields(installer, action=action, now=now)
    approval = StafferApproval(
        staffer_installer_id=installer.id,
        action=action,
        idempotency_key=idempotency_key,
        reason=reason,
    )
    db.add(approval)
    db.add(installer)
    db.commit()
    db.refresh(installer)
    event_type = "staffer.installer.approved" if action == "approve" else "staffer.installer.rejected"
    write_audit_event(
        db,
        event_type=event_type,
        staffer_installer_id=installer.id,
        details={"state": installer.state, "reason": reason, "idempotency_key": idempotency_key},
    )
    return _installer_out(installer)


@app.post("/staffer/installers/{installer_id}/approve", response_model=StafferInstallerOut)
def approve_staffer_installer(
    installer_id: str,
    req: StafferApprovalRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    installer = _get_installer_or_404(db, installer_id)
    return _handle_staffer_approval_action(
        installer=installer,
        db=db,
        action="approve",
        idempotency_key=idempotency_key,
        reason=req.reason,
    )


@app.post("/staffer/installers/{installer_id}/reject", response_model=StafferInstallerOut)
def reject_staffer_installer(
    installer_id: str,
    req: StafferApprovalRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    installer = _get_installer_or_404(db, installer_id)
    return _handle_staffer_approval_action(
        installer=installer,
        db=db,
        action="reject",
        idempotency_key=idempotency_key,
        reason=req.reason,
    )


@app.post("/staffer/installers/{installer_id}/validate-launch", response_model=StafferInstallerOut)
def validate_staffer_launch(
    installer_id: str,
    req: StafferLaunchValidationRequest,
    db: Session = Depends(get_db),
):
    installer = _get_installer_or_404(db, installer_id)
    _require_transition(installer, "validate-launch")
    now = datetime.now(timezone.utc)
    installer.updated_at = now
    installer.launch_validated_at = now
    installer.state = "launch_validated" if req.is_valid else "launch_validation_failed"
    validation = StafferLaunchValidation(
        staffer_installer_id=installer.id,
        is_valid=req.is_valid,
        details=req.details,
        checked_at=now,
    )
    db.merge(validation)
    db.add(installer)
    db.commit()
    db.refresh(installer)
    event_name = "staffer.installer.launch_validated" if req.is_valid else "staffer.installer.launch_validation_failed"
    write_audit_event(
        db,
        event_type=event_name,
        staffer_installer_id=installer.id,
        details={"state": installer.state, "validation_details": req.details},
    )
    return _installer_out(installer)


@app.post("/staffer/installers/{installer_id}/activate", response_model=StafferInstallerOut)
def activate_staffer_installer(installer_id: str, db: Session = Depends(get_db)):
    installer = _get_installer_or_404(db, installer_id)
    _require_transition(installer, "activate")
    now = datetime.now(timezone.utc)
    _set_transition_fields(installer, action="activate", now=now)
    db.add(installer)
    db.commit()
    db.refresh(installer)
    write_audit_event(
        db,
        event_type="staffer.installer.activated",
        staffer_installer_id=installer.id,
        details={"state": installer.state},
    )
    return _installer_out(installer)


@app.post("/staffer/installers/{installer_id}/rollback", response_model=StafferInstallerOut)
def rollback_staffer_installer(installer_id: str, db: Session = Depends(get_db)):
    installer = _get_installer_or_404(db, installer_id)
    _require_transition(installer, "rollback")
    now = datetime.now(timezone.utc)
    _set_transition_fields(installer, action="rollback", now=now)
    db.add(installer)
    db.commit()
    db.refresh(installer)
    write_audit_event(
        db,
        event_type="staffer.installer.rolled_back",
        staffer_installer_id=installer.id,
        details={"state": installer.state},
    )
    return _installer_out(installer)
