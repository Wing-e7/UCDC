from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import write_audit_event
from .config import get_settings, validate_settings_for_startup
from .cors_setup import add_cors
from .consent_hash import compute_consent_hash, resource_spec_dict_from_model
from .db import get_db, init_db
from .jwt_utils import encode_consent_token
from .logging_middleware import RequestLoggingMiddleware
from .models import AuditEvent, Consent
from .schemas import (
    AuditEventOut,
    ConsentMetadata,
    ConsentRequest,
    ConsentResponse,
    PublicUiConfig,
    RevokeResponse,
    StafferLocalRunOut,
    StafferLocalStatus,
)
from .staffer_local_bridge import (
    StafferAction,
    get_staffer_local_status,
    is_staffer_local_bridge_enabled,
    run_staffer_action,
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


app = FastAPI(title="UCDC Consent Service", version="0.1", lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")
add_cors(app)

_WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if _WEB_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=str(_WEB_DIR), html=True), name="ui")


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


@app.get("/public-config", response_model=PublicUiConfig)
def public_ui_config():
    """Expose host-facing service URLs and default agent id for /ui and third-party clients (no secrets)."""
    s = get_settings()
    return PublicUiConfig(
        consent_base_url=s.public_consent_base_url.rstrip("/"),
        orchestrator_base_url=s.public_orchestrator_base_url.rstrip("/"),
        agent_adapter_base_url=s.public_agent_adapter_base_url.rstrip("/"),
        default_agent_id=s.default_agent_id,
        staffer_local_bridge=is_staffer_local_bridge_enabled(),
    )


def _staffer_local_http(action: StafferAction) -> StafferLocalRunOut:
    try:
        return run_staffer_action(action)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.get("/local-staffer/status", response_model=StafferLocalStatus)
def staffer_local_status():
    return get_staffer_local_status()


@app.post("/local-staffer/setup", response_model=StafferLocalRunOut)
def staffer_local_setup():
    return _staffer_local_http("setup")


@app.post("/local-staffer/setup-new", response_model=StafferLocalRunOut)
def staffer_local_setup_new():
    return _staffer_local_http("setup_new")


@app.post("/local-staffer/execute", response_model=StafferLocalRunOut)
def staffer_local_execute():
    return _staffer_local_http("execute")


@app.post("/consents", response_model=ConsentResponse)
def issue_consent(req: ConsentRequest, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=req.ttl_seconds)

    consent_id = str(uuid.uuid4())
    spec_dict = resource_spec_dict_from_model(req.resource_spec)
    consent_hash = compute_consent_hash(
        user_id=req.user_id,
        agent_id=req.agent_id,
        resources=req.resources,
        manifest_version=req.manifest_version,
        resource_spec=spec_dict if spec_dict else None,
    )

    consent = Consent(
        id=consent_id,
        user_id=req.user_id,
        agent_id=req.agent_id,
        resources=req.resources,
        manifest_version=req.manifest_version,
        resource_spec=spec_dict,
        explanation=req.explanation,
        consent_hash=consent_hash,
        issued_at=now,
        expires_at=expires_at,
        revoked_at=None,
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)

    token = encode_consent_token(
        consent_id=consent.id,
        user_id=consent.user_id,
        agent_id=consent.agent_id,
        consent_hash=consent.consent_hash,
        expires_at=consent.expires_at,
    )
    write_audit_event(
        db,
        event_type="consent.issued",
        consent_id=consent.id,
        details={
            "user_id": consent.user_id,
            "agent_id": consent.agent_id,
            "resources": list(consent.resources or []),
            "manifest_version": consent.manifest_version,
            "resource_spec": dict(consent.resource_spec or {}),
            "ttl_seconds": req.ttl_seconds,
        },
    )
    return ConsentResponse(consent_id=consent.id, consent_token=token, expires_at=consent.expires_at)


@app.get("/consents/{consent_id}", response_model=ConsentMetadata)
def get_consent(consent_id: str, db: Session = Depends(get_db)):
    consent = db.get(Consent, consent_id)
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")

    return ConsentMetadata(
        consent_id=consent.id,
        user_id=consent.user_id,
        agent_id=consent.agent_id,
        resources=list(consent.resources or []),
        manifest_version=int(consent.manifest_version),
        resource_spec=dict(consent.resource_spec or {}),
        explanation=consent.explanation,
        issued_at=consent.issued_at,
        expires_at=consent.expires_at,
        revoked_at=consent.revoked_at,
    )


@app.post("/consents/{consent_id}/revoke", response_model=RevokeResponse)
def revoke_consent(consent_id: str, db: Session = Depends(get_db)):
    consent = db.get(Consent, consent_id)
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")
    if consent.revoked_at is None:
        consent.revoked_at = datetime.now(timezone.utc)
        db.add(consent)
        db.commit()
        db.refresh(consent)
        write_audit_event(
            db,
            event_type="consent.revoked",
            consent_id=consent.id,
            details={"revoked_at": consent.revoked_at.isoformat()},
        )
    revoked_at = consent.revoked_at
    if revoked_at is None:
        raise HTTPException(status_code=409, detail="Consent could not be revoked")
    return RevokeResponse(consent_id=consent.id, revoked_at=revoked_at)


@app.get("/consents/{consent_id}/events", response_model=list[AuditEventOut])
def list_consent_events(consent_id: str, db: Session = Depends(get_db)):
    consent = db.get(Consent, consent_id)
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")
    rows = (
        db.execute(select(AuditEvent).where(AuditEvent.consent_id == consent_id).order_by(AuditEvent.created_at))
        .scalars()
        .all()
    )
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

