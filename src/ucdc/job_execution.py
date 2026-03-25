from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .adapter_client import call_adapter_execute
from .audit import write_audit_event
from .config import get_settings
from .consent_hash import consent_hash_from_job_manifest
from .jwt_utils import encode_consent_token
from .models import Consent, Job
from .schemas import JobManifest

logger = logging.getLogger("ucdc")


def verify_manifest_matches_consent(*, consent: Consent, manifest: JobManifest) -> None:
    expected = consent_hash_from_job_manifest(user_id=consent.user_id, manifest=manifest)
    if expected != consent.consent_hash:
        raise ValueError("Job manifest does not match stored consent hash")


def resolve_consent_token(*, consent: Consent, explicit_token: str | None) -> str:
    if explicit_token is not None:
        return explicit_token
    return encode_consent_token(
        consent_id=consent.id,
        user_id=consent.user_id,
        agent_id=consent.agent_id,
        consent_hash=consent.consent_hash,
        expires_at=consent.expires_at,
    )


def run_adapter_and_finalize(
    db: Session,
    job: Job,
    consent: Consent,
    manifest: JobManifest,
    *,
    consent_token: str | None = None,
) -> None:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    job.status = "running"
    job.started_at = now
    job.updated_at = now
    db.add(job)
    db.commit()
    db.refresh(job)
    write_audit_event(
        db,
        event_type="job.running",
        consent_id=consent.id,
        job_id=job.id,
        details={},
    )

    token = resolve_consent_token(consent=consent, explicit_token=consent_token)

    try:
        call_adapter_execute(
            settings.agent_adapter_base_url,
            token,
            job.id,
            manifest.model_dump(),
            timeout_seconds=settings.agent_adapter_timeout_seconds,
        )
    except Exception as e:
        fin = datetime.now(timezone.utc)
        job.status = "failed"
        job.last_error = str(e)[:8000]
        job.finished_at = fin
        job.updated_at = fin
        db.add(job)
        db.commit()
        db.refresh(job)
        write_audit_event(
            db,
            event_type="job.failed",
            consent_id=consent.id,
            job_id=job.id,
            details={"error": str(e)},
        )
        logger.warning("job_failed", extra={"job_id": job.id, "error": str(e)})
        return

    fin = datetime.now(timezone.utc)
    job.status = "completed"
    job.finished_at = fin
    job.updated_at = fin
    job.last_error = None
    db.add(job)
    db.commit()
    db.refresh(job)
    write_audit_event(
        db,
        event_type="job.completed",
        consent_id=consent.id,
        job_id=job.id,
        details={},
    )
