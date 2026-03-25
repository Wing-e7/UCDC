import uuid

from fastapi.testclient import TestClient

from ucdc.consent_api import app as consent_app
from ucdc.consent_hash import compute_consent_hash, consent_hash_from_job_manifest
from ucdc.db import get_sessionmaker
from ucdc.job_worker import run_once
from ucdc.models import AgentEntitlement
from ucdc.orchestrator_api import app as orchestrator_app
from ucdc.schemas import JobManifest, ResourceSpec


def _clear_settings_cache():
    from ucdc.config import get_settings

    get_settings.cache_clear()


def test_legacy_hash_unchanged_for_v1_empty_spec():
    h1 = compute_consent_hash(user_id="u", agent_id="a", resources=["r1"])
    h2 = compute_consent_hash(user_id="u", agent_id="a", resources=["r1"], manifest_version=1, resource_spec=None)
    assert h1 == h2


def test_extended_hash_when_resource_spec_set():
    h_legacy = compute_consent_hash(user_id="u", agent_id="a", resources=["r1"])
    h_ext = compute_consent_hash(
        user_id="u",
        agent_id="a",
        resources=["r1"],
        manifest_version=1,
        resource_spec={"compute_class": "gpu"},
    )
    assert h_ext != h_legacy


def test_consent_hash_from_manifest_matches_compute():
    m = JobManifest(
        agent_id="example-agent",
        resources=["s3://x"],
        manifest_version=2,
        resource_spec=ResourceSpec(compute_class="standard", capability_tags=["batch"]),
    )
    direct = compute_consent_hash(
        user_id="u1",
        agent_id="example-agent",
        resources=["s3://x"],
        manifest_version=2,
        resource_spec={"capability_tags": ["batch"], "compute_class": "standard"},
    )
    assert consent_hash_from_job_manifest(user_id="u1", manifest=m) == direct


def test_manifest_v2_end_to_end(monkeypatch):
    _clear_settings_cache()
    monkeypatch.setenv("UCDC_SKIP_ADAPTER_INTEGRATION", "1")
    with TestClient(consent_app) as consent_client, TestClient(orchestrator_app) as orchestrator_client:
        consent_resp = consent_client.post(
            "/consents",
            json={
                "user_id": "user-123",
                "agent_id": "example-agent",
                "resources": ["s3://bucket/a"],
                "explanation": "v2",
                "ttl_seconds": 3600,
                "manifest_version": 2,
                "resource_spec": {"compute_class": "gpu", "capability_tags": ["inference"]},
            },
        )
        assert consent_resp.status_code == 200, consent_resp.text
        token = consent_resp.json()["consent_token"]

        bad = orchestrator_client.post(
            "/jobs",
            json={
                "consent_token": token,
                "job_manifest": {
                    "agent_id": "example-agent",
                    "resources": ["s3://bucket/a"],
                    "data": {},
                    "manifest_version": 2,
                    "resource_spec": {"compute_class": "cpu", "capability_tags": ["inference"]},
                },
            },
        )
        assert bad.status_code == 403

        good = orchestrator_client.post(
            "/jobs",
            json={
                "consent_token": token,
                "job_manifest": {
                    "agent_id": "example-agent",
                    "resources": ["s3://bucket/a"],
                    "data": {},
                    "manifest_version": 2,
                    "resource_spec": {"compute_class": "gpu", "capability_tags": ["inference"]},
                },
            },
        )
        assert good.status_code == 200
        assert good.json()["status"] == "scheduled"


def test_enqueue_admission_429(monkeypatch):
    _clear_settings_cache()
    monkeypatch.setenv("UCDC_SKIP_ADAPTER_INTEGRATION", "1")
    monkeypatch.delenv("UCDC_DEFAULT_MAX_CONCURRENT_JOBS", raising=False)
    _clear_settings_cache()

    uid = "user-ent-429"

    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        ent = AgentEntitlement(
            id=str(uuid.uuid4()),
            user_id=uid,
            agent_id="example-agent",
            max_concurrent_jobs=1,
        )
        db.add(ent)
        db.commit()
    finally:
        db.close()

    with TestClient(consent_app) as consent_client, TestClient(orchestrator_app) as orchestrator_client:
        consent_resp = consent_client.post(
            "/consents",
            json={
                "user_id": uid,
                "agent_id": "example-agent",
                "resources": ["s3://bucket/a"],
                "explanation": "admission",
                "ttl_seconds": 3600,
            },
        )
        token = consent_resp.json()["consent_token"]
        manifest = {"agent_id": "example-agent", "resources": ["s3://bucket/a"], "data": {}}

        j1 = orchestrator_client.post("/jobs", json={"consent_token": token, "job_manifest": manifest})
        assert j1.status_code == 200

        j2 = orchestrator_client.post("/jobs", json={"consent_token": token, "job_manifest": manifest})
        assert j2.status_code == 429


def test_async_job_completed_by_worker(monkeypatch):
    _clear_settings_cache()
    monkeypatch.setenv("UCDC_ASYNC_JOBS", "true")
    monkeypatch.delenv("UCDC_SKIP_ADAPTER_INTEGRATION", raising=False)
    _clear_settings_cache()

    calls = {"n": 0}

    def _fake_execute(base_url, consent_token, job_id, job_manifest, timeout_seconds=30.0):
        calls["n"] += 1
        return {"job_id": job_id, "status": "completed", "result": {}}

    monkeypatch.setattr("ucdc.job_execution.call_adapter_execute", _fake_execute)

    with TestClient(consent_app) as consent_client, TestClient(orchestrator_app) as orchestrator_client:
        consent_resp = consent_client.post(
            "/consents",
            json={
                "user_id": "user-456",
                "agent_id": "example-agent",
                "resources": ["s3://bucket/b"],
                "explanation": "async",
                "ttl_seconds": 3600,
            },
        )
        token = consent_resp.json()["consent_token"]
        job_resp = orchestrator_client.post(
            "/jobs",
            json={
                "consent_token": token,
                "job_manifest": {"agent_id": "example-agent", "resources": ["s3://bucket/b"], "data": {}},
            },
        )
        assert job_resp.status_code == 202
        job_id = job_resp.json()["job_id"]
        assert job_resp.json()["status"] == "queued"

        assert run_once() is True
        assert calls["n"] == 1

        detail = orchestrator_client.get(f"/jobs/{job_id}")
        assert detail.status_code == 200
        assert detail.json()["status"] == "completed"
