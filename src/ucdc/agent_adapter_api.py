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
from .models import Consent
from .schemas import CapabilitiesResponse, ExecuteRequest, ExecuteResponse

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


app = FastAPI(title="UCDC Agent Adapter (Example)", version="0.1", lifespan=lifespan)
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


@app.get("/capabilities", response_model=CapabilitiesResponse)
def capabilities():
    return CapabilitiesResponse(agent_id="example-agent", capabilities=["echo", "noop-execute"])


@app.post("/execute", response_model=ExecuteResponse)
def execute(req: ExecuteRequest, db: Session = Depends(get_db)):
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
    if consent.revoked_at is not None:
        raise HTTPException(status_code=403, detail="Consent invalid")

    now = datetime.now(timezone.utc)
    expires_at = consent.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise HTTPException(status_code=403, detail="Consent expired")

    # Skeleton behavior: accept execution requests and return a deterministic result.
    write_audit_event(
        db,
        event_type="agent.execute.completed",
        consent_id=consent_id,
        job_id=req.job_id,
        details={"agent_id": manifest.agent_id},
    )
    return ExecuteResponse(
        job_id=req.job_id,
        status="completed",
        result={"agent_id": req.job_manifest.agent_id, "resources": req.job_manifest.resources, "note": "noop"},
    )

