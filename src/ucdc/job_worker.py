from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import write_audit_event
from .config import get_settings, validate_settings_for_startup
from .db import get_engine, get_sessionmaker
from .entitlements import enforce_dequeue_admission
from .job_execution import run_adapter_and_finalize, verify_manifest_matches_consent
from .models import Consent, Job
from .schemas import JobManifest

logger = logging.getLogger("ucdc.worker")


def _process_one_session(db: Session) -> bool:
    job = (
        db.scalars(
            select(Job)
            .where(Job.status == "queued")
            .order_by(Job.created_at)
            .limit(1)
            .with_for_update()
        ).first()
    )
    if job is None:
        return False

    consent = db.get(Consent, job.consent_id)
    now = datetime.now(timezone.utc)

    if not consent:
        job.status = "failed"
        job.last_error = "Consent row missing for job"
        job.finished_at = now
        job.updated_at = now
        db.add(job)
        db.commit()
        return True

    if consent.revoked_at is not None:
        job.status = "failed"
        job.last_error = "Consent revoked before execution"
        job.finished_at = now
        job.updated_at = now
        db.add(job)
        db.commit()
        return True

    expires_at = consent.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        job.status = "failed"
        job.last_error = "Consent expired before execution"
        job.finished_at = now
        job.updated_at = now
        db.add(job)
        db.commit()
        return True

    manifest = JobManifest.model_validate(dict(job.payload or {}))

    try:
        verify_manifest_matches_consent(consent=consent, manifest=manifest)
    except ValueError as e:
        job.status = "failed"
        job.last_error = str(e)[:8000]
        job.finished_at = now
        job.updated_at = now
        db.add(job)
        db.commit()
        return True

    try:
        enforce_dequeue_admission(
            db,
            user_id=consent.user_id,
            agent_id=job.agent_id,
            job_id=job.id,
        )
    except RuntimeError as e:
        job.status = "failed"
        job.last_error = str(e)[:8000]
        job.finished_at = now
        job.updated_at = now
        db.add(job)
        db.commit()
        write_audit_event(
            db,
            event_type="job.admission_denied",
            consent_id=consent.id,
            job_id=job.id,
            details={"phase": "dequeue", "error": str(e)},
        )
        return True

    run_adapter_and_finalize(db, job, consent, manifest, consent_token=None)
    return True


def run_once() -> bool:
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        return _process_one_session(db)
    finally:
        db.close()


def main() -> None:
    validate_settings_for_startup()
    get_engine()
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    logger.info("job_worker_start", extra={"poll_s": settings.worker_poll_seconds})
    while True:
        try:
            did = run_once()
            if not did:
                time.sleep(settings.worker_poll_seconds)
        except KeyboardInterrupt:
            logger.info("job_worker_stop")
            sys.exit(0)
        except Exception:
            logger.exception("job_worker_iteration_failed")
            time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
