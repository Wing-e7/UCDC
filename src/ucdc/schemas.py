from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ResourceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    compute_class: Optional[str] = Field(default=None, description="e.g. standard, cpu_heavy, gpu")
    max_runtime_seconds: Optional[int] = Field(default=None, ge=1)
    capability_tags: List[str] = Field(default_factory=list)


class ConsentRequest(BaseModel):
    user_id: str
    agent_id: str
    resources: List[str] = Field(default_factory=list)
    explanation: str
    ttl_seconds: int = Field(default=3600, ge=60, le=60 * 60 * 24 * 30)
    manifest_version: int = Field(default=1, ge=1, le=100)
    resource_spec: Optional[ResourceSpec] = None


class ConsentResponse(BaseModel):
    consent_id: str
    consent_token: str
    expires_at: datetime


class ConsentMetadata(BaseModel):
    consent_id: str
    user_id: str
    agent_id: str
    resources: List[str]
    manifest_version: int
    resource_spec: Dict[str, Any]
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
    manifest_version: int = Field(default=1, ge=1, le=100)
    resource_spec: Optional[ResourceSpec] = None


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
    staffer_installer_id: Optional[str] = None
    event_type: str
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class StafferInstallerCreateRequest(BaseModel):
    payload: Dict[str, Any] = Field(default_factory=dict)


class StafferApprovalRequest(BaseModel):
    reason: Optional[str] = None


class StafferLaunchValidationRequest(BaseModel):
    is_valid: bool = True
    details: Dict[str, Any] = Field(default_factory=dict)


class StafferInstallerOut(BaseModel):
    id: str
    state: str
    payload: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    launch_validated_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    rolled_back_at: Optional[datetime] = None


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
