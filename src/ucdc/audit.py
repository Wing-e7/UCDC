from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from .models import AuditEvent


def write_audit_event(
    db: Session,
    *,
    event_type: str,
    consent_id: Optional[str] = None,
    job_id: Optional[str] = None,
    details: Dict[str, Any] | None = None,
) -> AuditEvent:
    ev = AuditEvent(
        consent_id=consent_id,
        job_id=job_id,
        event_type=event_type,
        details=details or {},
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev

