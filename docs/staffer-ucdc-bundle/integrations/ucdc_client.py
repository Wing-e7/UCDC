"""
Minimal UCDC client for agent apps (e.g. The Staffer).

Copy into the Staffer repo under integrations/ucdc/ — no UCDC dependency required
beyond httpx (add to Staffer requirements.txt).

Environment:
  UCDC_CONSENT_BASE_URL       default http://127.0.0.1:8001
  UCDC_ORCHESTRATOR_BASE_URL  default http://127.0.0.1:8002
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import httpx


class UCDCClientError(Exception):
    pass


class UCDCClient:
    def __init__(
        self,
        *,
        consent_base_url: Optional[str] = None,
        orchestrator_base_url: Optional[str] = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.consent_base = (consent_base_url or os.getenv("UCDC_CONSENT_BASE_URL") or "http://127.0.0.1:8001").rstrip(
            "/"
        )
        self.orch_base = (
            orchestrator_base_url or os.getenv("UCDC_ORCHESTRATOR_BASE_URL") or "http://127.0.0.1:8002"
        ).rstrip("/")
        self.timeout = timeout_seconds

    def issue_consent(
        self,
        *,
        user_id: str,
        agent_id: str,
        resources: List[str],
        explanation: str,
        ttl_seconds: int = 3600,
        manifest_version: int = 1,
        resource_spec: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "user_id": user_id,
            "agent_id": agent_id,
            "resources": resources,
            "explanation": explanation,
            "ttl_seconds": ttl_seconds,
            "manifest_version": manifest_version,
        }
        if resource_spec is not None:
            body["resource_spec"] = resource_spec
        with httpx.Client(timeout=self.timeout) as c:
            r = c.post(f"{self.consent_base}/consents", json=body)
        if r.status_code >= 400:
            raise UCDCClientError(f"consent issue failed: {r.status_code} {r.text}")
        return r.json()

    def schedule_job(
        self,
        *,
        consent_token: str,
        agent_id: str,
        resources: List[str],
        data: Optional[Dict[str, Any]] = None,
        manifest_version: int = 1,
        resource_spec: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        manifest: Dict[str, Any] = {
            "agent_id": agent_id,
            "resources": resources,
            "data": data or {},
            "manifest_version": manifest_version,
        }
        if resource_spec is not None:
            manifest["resource_spec"] = resource_spec
        with httpx.Client(timeout=self.timeout) as c:
            r = c.post(
                f"{self.orch_base}/jobs",
                json={"consent_token": consent_token, "job_manifest": manifest},
            )
        if r.status_code not in (200, 202):
            raise UCDCClientError(f"schedule job failed: {r.status_code} {r.text}")
        return r.json()

    def get_job(self, job_id: str) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as c:
            r = c.get(f"{self.orch_base}/jobs/{job_id}")
        r.raise_for_status()
        return r.json()

    def revoke_consent(self, consent_id: str) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as c:
            r = c.post(f"{self.consent_base}/consents/{consent_id}/revoke")
        r.raise_for_status()
        return r.json()

    def wait_for_terminal_job(
        self,
        job_id: str,
        *,
        poll_seconds: float = 0.5,
        max_wait_seconds: float = 120.0,
    ) -> Dict[str, Any]:
        deadline = time.monotonic() + max_wait_seconds
        terminal = {"completed", "failed", "cancelled"}
        while time.monotonic() < deadline:
            j = self.get_job(job_id)
            if j.get("status") in terminal:
                return j
            time.sleep(poll_seconds)
        raise UCDCClientError(f"job {job_id} did not reach terminal status within {max_wait_seconds}s")

    def consent_job_and_wait(
        self,
        *,
        user_id: str,
        agent_id: str,
        resources: List[str],
        explanation: str,
        job_data: Optional[Dict[str, Any]] = None,
        manifest_version: int = 1,
        resource_spec: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Issue consent, schedule job, poll until terminal. Handles sync (200) and async (202) orchestration.
        """
        c = self.issue_consent(
            user_id=user_id,
            agent_id=agent_id,
            resources=resources,
            explanation=explanation,
            manifest_version=manifest_version,
            resource_spec=resource_spec,
        )
        token = c["consent_token"]
        sched = self.schedule_job(
            consent_token=token,
            agent_id=agent_id,
            resources=resources,
            data=job_data,
            manifest_version=manifest_version,
            resource_spec=resource_spec,
        )
        job_id = sched["job_id"]
        return self.wait_for_terminal_job(job_id)


def _smoke() -> None:
    """Manual smoke: requires UCDC stack up and default agent_id resolvable."""
    client = UCDCClient()
    out = client.consent_job_and_wait(
        user_id="smoke-user",
        agent_id="example-agent",
        resources=["s3://smoke/test"],
        explanation="Staffer ucdc_client smoke test",
        job_data={"smoke": True},
    )
    print(out)


if __name__ == "__main__":
    _smoke()
