from __future__ import annotations

from typing import Any, Dict

import httpx


def call_adapter_execute(
    base_url: str,
    consent_token: str,
    job_id: str,
    job_manifest: Dict[str, Any],
    *,
    timeout_seconds: float = 30.0,
) -> Dict[str, Any]:
    """POST /execute on the agent adapter; raises httpx.HTTPError on transport/HTTP errors."""
    url = f"{base_url.rstrip('/')}/execute"
    with httpx.Client(timeout=timeout_seconds) as client:
        r = client.post(
            url,
            json={
                "consent_token": consent_token,
                "job_id": job_id,
                "job_manifest": job_manifest,
            },
        )
        r.raise_for_status()
        return r.json()
