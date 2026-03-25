from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConsentRequest(BaseModel):
    user_id: str
    agent_id: str
    resources: List[str] = Field(default_factory=list)
    explanation: str
    ttl_seconds: int = Field(default=3600, ge=60, le=60 * 60 * 24 * 30)


class ConsentResponse(BaseModel):
    consent_id: str
    consent_token: str
    expires_at: datetime


class ConsentMetadata(BaseModel):
    consent_id: str
    user_id: str
    agent_id: str
    resources: List[str]
    explanation: Optional[str]
    issued_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime]


class RevokeResponse(BaseModel):
    consent_id: str
    revoked_at: datetime


class JobManifest(BaseModel):
    agent_id: str
    resources: List[str] = Field(default_factory=list)
    data: Dict[str, Any] = Field(default_factory=dict)


class JobRequest(BaseModel):
    consent_token: str
    job_manifest: JobManifest


class JobResponse(BaseModel):
    job_id: str
    status: str


class JobDetail(BaseModel):
    job_id: str
    consent_id: str
    agent_id: str
    status: str
    payload: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    last_error: Optional[str] = None


class JobCancelResponse(BaseModel):
    job_id: str
    status: str
    cancelled_at: datetime


class AuditEventOut(BaseModel):
    id: str
    consent_id: Optional[str] = None
    job_id: Optional[str] = None
    event_type: str
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class CapabilitiesResponse(BaseModel):
    agent_id: str
    capabilities: List[str]


class ExecuteRequest(BaseModel):
    consent_token: str
    job_id: str
    job_manifest: JobManifest


class ExecuteResponse(BaseModel):
    job_id: str
    status: str
    result: Dict[str, Any]

