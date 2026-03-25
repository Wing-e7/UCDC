from __future__ import annotations

import hashlib
import json
from typing import Any, List

from .schemas import JobManifest, ResourceSpec


def _normalize_resource_spec_dict(spec: dict[str, Any]) -> dict[str, Any]:
    out = dict(spec)
    if "capability_tags" in out and out["capability_tags"] is not None:
        out["capability_tags"] = sorted(out["capability_tags"])
    return out


def resource_spec_dict_from_model(spec: ResourceSpec | None) -> dict[str, Any]:
    if spec is None:
        return {}
    data = spec.model_dump(mode="json", exclude_none=True)
    return _normalize_resource_spec_dict(data)


def compute_consent_hash(
    *,
    user_id: str,
    agent_id: str,
    resources: List[str],
    manifest_version: int = 1,
    resource_spec: dict[str, Any] | None = None,
) -> str:
    """SHA-256 over a canonical JSON payload.

    Legacy mode (backward compatible with v0 seeds): ``manifest_version == 1`` and an empty
    ``resource_spec`` uses only ``user_id``, ``agent_id``, and ``resources`` so existing tokens
    and tests keep stable hashes. Any non-empty resource spec or ``manifest_version > 1`` uses
    the extended payload that binds structured capacity.
    """
    spec = _normalize_resource_spec_dict(dict(resource_spec or {}))
    use_legacy = manifest_version == 1 and len(spec) == 0
    if use_legacy:
        payload: dict[str, Any] = {"user_id": user_id, "agent_id": agent_id, "resources": list(resources)}
    else:
        payload = {
            "user_id": user_id,
            "agent_id": agent_id,
            "resources": list(resources),
            "manifest_version": manifest_version,
            "resource_spec": spec,
        }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def consent_hash_from_job_manifest(*, user_id: str, manifest: JobManifest) -> str:
    spec = resource_spec_dict_from_model(manifest.resource_spec)
    return compute_consent_hash(
        user_id=user_id,
        agent_id=manifest.agent_id,
        resources=list(manifest.resources),
        manifest_version=manifest.manifest_version,
        resource_spec=spec if spec else None,
    )
